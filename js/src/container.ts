import JSZip from "jszip";
import { CcxSecurityError, CcxValidationError } from "./errors";
import {
  MIMETYPE,
  MIMETYPE_PATH,
  MAX_ENTRIES,
  MAX_ENTRY_UNCOMPRESSED,
  MAX_TOTAL_UNCOMPRESSED,
} from "./constants";

/**
 * A hardened, read-only view over a `.ccx` ZIP archive.
 *
 * Port-of-record: `src/ccx/container.py`. jszip does not cleanly expose per-entry
 * compression method or guaranteed first-entry order, both of which the `mimetype`
 * rule needs. So the first local file header is parsed directly from the raw buffer
 * for `checkMimetype()`, and jszip is used for everything else (entry enumeration,
 * reads, `unixPermissions` for symlinks, `_data.uncompressedSize` for size bounds).
 */
export class Container {
  private constructor(
    private zip: JSZip,
    private buf: Uint8Array,
    readonly names: string[],
  ) {}

  static async load(bytes: Uint8Array): Promise<Container> {
    let zip: JSZip;
    try {
      zip = await JSZip.loadAsync(bytes);
    } catch (e) {
      throw new CcxValidationError(`not a valid ZIP: ${(e as Error).message}`);
    }
    const names = Object.keys(zip.files).filter((n) => !zip.files[n].dir);
    const c = new Container(zip, bytes, names);
    c.checkSafety(); // throws CcxSecurityError
    return c;
  }

  private checkSafety(): void {
    if (this.names.length > MAX_ENTRIES)
      throw new CcxSecurityError(`too many entries: ${this.names.length} > ${MAX_ENTRIES}`);

    // Path safety must run on the RAW entry names from the local file headers.
    // jszip silently normalizes traversal (`../evil.txt` -> `evil.txt`) when it
    // builds `zip.files`, so its keys can never reveal a traversal — the Python
    // oracle reads `ZipInfo.filename` verbatim, which preserves `..`. Parse the
    // raw header names ourselves (same "don't trust jszip" pattern as the
    // mimetype check) so we match the reference verdict.
    for (const name of this.rawEntryNames()) {
      const parts = name.split("/");
      if (name.startsWith("/") || /^[A-Za-z]:/.test(name) || parts.includes(".."))
        throw new CcxSecurityError(`unsafe path in archive: ${name}`);
    }

    let total = 0;
    for (const name of Object.keys(this.zip.files)) {
      const f = this.zip.files[name];
      // symlink: unix mode S_IFLNK (0xA000)
      const mode = (f as any).unixPermissions ?? 0;
      if ((mode & 0xf000) === 0xa000) throw new CcxSecurityError(`symlink not allowed: ${name}`);
      const size = (f as any)._data?.uncompressedSize ?? 0;
      if (size > MAX_ENTRY_UNCOMPRESSED)
        throw new CcxSecurityError(`entry too large (zip bomb?): ${name}`);
      total += size;
    }
    if (total > MAX_TOTAL_UNCOMPRESSED)
      throw new CcxSecurityError(`archive too large uncompressed (zip bomb?): ${total}`);
  }

  /**
   * Extract every entry name verbatim by scanning the raw buffer for local
   * file header signatures (PK\x03\x04). Reading only the signature + name
   * length + name avoids striding by (possibly absent) sizes, which is
   * unreliable when entries use a trailing data descriptor.
   */
  private rawEntryNames(): string[] {
    const b = this.buf;
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    const names: string[] = [];
    const decoder = new TextDecoder();
    // Stop at the central directory (PK\x01\x02); only local headers carry names
    // we care about, and the same name also appears in the central directory.
    for (let off = 0; off + 30 <= b.length; off++) {
      if (dv.getUint32(off, true) !== 0x04034b50) continue;
      const nameLen = dv.getUint16(off + 26, true);
      const extraLen = dv.getUint16(off + 28, true);
      if (off + 30 + nameLen > b.length) continue;
      names.push(decoder.decode(b.subarray(off + 30, off + 30 + nameLen)));
      // Skip past this header + name + extra so a byte sequence inside the name
      // or extra field cannot be misread as another header signature.
      off += 30 + nameLen + extraLen - 1;
    }
    return names;
  }

  checkMimetype(): void {
    // Parse the FIRST local file header from the raw bytes (jszip won't tell us
    // order + compression reliably). ZIP local header: sig PK\x03\x04 (4),
    // ... compression method at offset 8 (2 bytes, LE; 0 = STORED) ...
    // name length at 26 (2), extra length at 28 (2), name at 30.
    const b = this.buf;
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    if (dv.getUint32(0, true) !== 0x04034b50)
      throw new CcxValidationError("first archive entry must be 'mimetype'");
    const method = dv.getUint16(8, true);
    const nameLen = dv.getUint16(26, true);
    const extraLen = dv.getUint16(28, true);
    const name = new TextDecoder().decode(b.subarray(30, 30 + nameLen));
    if (name !== MIMETYPE_PATH)
      throw new CcxValidationError("first archive entry must be 'mimetype'");
    if (method !== 0)
      throw new CcxValidationError("'mimetype' must be stored uncompressed (ZIP STORED)");
    const dataStart = 30 + nameLen + extraLen;
    const value = new TextDecoder().decode(b.subarray(dataStart, dataStart + MIMETYPE.length)).trim();
    if (value !== MIMETYPE)
      throw new CcxValidationError(`mimetype must be '${MIMETYPE}', got '${value}'`);
  }

  has(path: string): boolean {
    return this.names.includes(path);
  }

  async read(path: string): Promise<Uint8Array> {
    const f = this.zip.file(path);
    if (!f) throw new CcxValidationError(`missing entry: ${path}`);
    return f.async("uint8array");
  }

  async readText(path: string): Promise<string> {
    return new TextDecoder("utf-8").decode(await this.read(path));
  }
}
