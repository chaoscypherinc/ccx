/**
 * High-level CCX package object: open, inspect, validate (Core level).
 *
 * Port-of-record: `src/ccx/package.py`. `openPackage()` opens + parses the
 * manifest (rejecting malformed/missing/schema-invalid manifests and unsafe
 * archives at open). `CcxPackage.validate()` runs Core validation in the exact
 * Python sequence and then probes the higher conformance classes.
 *
 * Vendor-neutral: no `chaoscypher.*` knowledge. `computeStats()` is a generic
 * RDF-Dataset view (entities vs. `ccx:Relationship` resources in the default
 * graph + a source count), nothing application-specific.
 */

import { CHECKERS } from "./conformance";
import { Container } from "./container";
import { verify } from "./checksums";
import { isDefault, rejectRemoteContext } from "./graphs";
import { loadManifest } from "./manifest";
import { RESERVED_PQC_FORMATS, verifyEd25519 } from "./signing";
import {
  CCX_VERSION,
  CONTEXT_PATH,
  MANIFEST_PATH,
  SHAPES_PATH,
  SOURCES_PATH,
} from "./constants";
import { CcxError, CcxSecurityError, CcxValidationError } from "./errors";
import type {
  CcxManifest,
  GraphDocument,
  PackageStats,
  SignatureResult,
  ValidationReport,
  CcxClass,
} from "./types";

const UNSET = Symbol("unset");

/** An opened CCX package. The manifest is parsed eagerly; graphs/context are lazy. */
export class CcxPackage {
  readonly container: Container;
  readonly manifest: CcxManifest;
  private _context: unknown = UNSET;

  constructor(container: Container, manifest: CcxManifest) {
    this.container = container;
    this.manifest = manifest;
  }

  /** Parse and cache `context.jsonld`. Throws `CcxValidationError` if not JSON. */
  async context(): Promise<unknown> {
    if (this._context === UNSET) {
      const raw = await this.container.readText(CONTEXT_PATH);
      try {
        this._context = JSON.parse(raw);
      } catch (exc) {
        throw new CcxValidationError(`${CONTEXT_PATH} is not valid JSON: ${(exc as Error).message}`);
      }
    }
    return this._context;
  }

  /**
   * Core validation, mirroring `package.py` step-for-step. The mimetype check is
   * a *caught, accumulated* error (it never throws out of `validate()`); a
   * present-but-malformed extension surfaces warnings but never fails Core.
   */
  async validate(): Promise<ValidationReport> {
    const errors: string[] = [];
    const warnings: string[] = [];

    // (1) mimetype — caught + accumulated, NOT thrown.
    try {
      this.container.checkMimetype();
    } catch (exc) {
      if (exc instanceof CcxError) {
        errors.push(String(exc.message));
      } else {
        throw exc;
      }
    }

    // (2) version mismatch — warning.
    if (this.manifest.ccxVersion !== CCX_VERSION) {
      warnings.push(
        `ccx_version ${JSON.stringify(this.manifest.ccxVersion)} != supported ${JSON.stringify(CCX_VERSION)}`,
      );
    }

    // (3) context present + parses + no remote context — errors.
    if (!this.container.has(CONTEXT_PATH)) {
      errors.push(`missing ${CONTEXT_PATH}`);
    } else {
      let contextDoc: unknown;
      let parsed = true;
      try {
        contextDoc = await this.context();
      } catch (exc) {
        if (exc instanceof CcxValidationError) {
          errors.push(String(exc.message));
          parsed = false;
        } else {
          throw exc;
        }
      }
      if (parsed) {
        try {
          rejectRemoteContext(contextDoc);
        } catch (exc) {
          if (exc instanceof CcxSecurityError) {
            errors.push(`${CONTEXT_PATH}: ${exc.message}`);
          } else {
            throw exc;
          }
        }
      }
    }

    // (4) graphs non-empty (error) + at least one default graph (warning).
    if (this.manifest.graphs.length === 0) {
      errors.push("no graphs declared");
    } else if (!this.manifest.graphs.some((g) => isDefault(g))) {
      warnings.push("no default/core graph (role='default' or namespace='ccx')");
    }

    // (5) each declared graph + asset: exists + checksums + (graphs) parse + no remote context.
    const graphPaths = new Set(this.manifest.graphs.map((g) => g.path));
    for (const entry of [...this.manifest.graphs, ...this.manifest.assets]) {
      if (!this.container.has(entry.path)) {
        errors.push(`declared file missing: ${entry.path}`);
        continue;
      }
      const data = await this.container.read(entry.path);
      if (!verify(data, entry.sha256, entry.sha512)) {
        errors.push(`checksum mismatch: ${entry.path}`);
        continue;
      }
      if (graphPaths.has(entry.path)) {
        let doc: unknown;
        try {
          doc = JSON.parse(new TextDecoder("utf-8").decode(data));
        } catch (exc) {
          errors.push(`${entry.path} is not valid JSON: ${(exc as Error).message}`);
          continue;
        }
        try {
          rejectRemoteContext(doc);
        } catch (exc) {
          if (exc instanceof CcxSecurityError) {
            errors.push(`${entry.path}: ${exc.message}`);
          } else {
            throw exc;
          }
        }
      }
    }

    // (6) no license — warning.
    if (this.manifest.license === null) {
      warnings.push("no license declared (recommended)");
    }

    // (7) Core passed? Probe the higher conformance classes.
    const ok = errors.length === 0;
    const classes: CcxClass[] = [];
    if (ok) {
      classes.push("core");
      for (const [clsName, checker] of CHECKERS) {
        const { present, issues } = await checker(this);
        if (!present) continue;
        if (issues.length > 0) {
          for (const issue of issues) warnings.push(`${clsName}: ${issue}`);
        } else {
          classes.push(clsName as CcxClass);
        }
      }
    }

    return {
      ok,
      errors,
      warnings,
      conformanceLevel: ok ? "core" : null,
      classes,
    };
  }

  /** Return each declared graph's raw on-disk JSON-LD document. */
  async graphDocuments(): Promise<GraphDocument[]> {
    const out: GraphDocument[] = [];
    for (const g of this.manifest.graphs) {
      const raw = await this.container.readText(g.path);
      let doc: unknown;
      try {
        doc = JSON.parse(raw);
      } catch (exc) {
        throw new CcxValidationError(`${g.path} is not valid JSON: ${(exc as Error).message}`);
      }
      out.push({ namespace: g.namespace, name: g.name, role: g.role ?? null, path: g.path, doc });
    }
    return out;
  }

  /** Return the raw bytes of a declared asset by its manifest path. */
  async assetBytes(path: string): Promise<Uint8Array> {
    if (!this.manifest.assets.some((a) => a.path === path)) {
      throw new CcxValidationError(`no such declared asset: ${JSON.stringify(path)}`);
    }
    return this.container.read(path);
  }

  /** Parse `sources.jsonl` (Core + Sources) into records. Returns [] if absent. */
  async sources(): Promise<Record<string, unknown>[]> {
    if (!this.container.has(SOURCES_PATH)) return [];
    const raw = await this.container.readText(SOURCES_PATH);
    const out: Record<string, unknown>[] = [];
    const lines = raw.split(/\r\n|\r|\n/);
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line.trim()) continue;
      try {
        out.push(JSON.parse(line) as Record<string, unknown>);
      } catch (exc) {
        throw new CcxValidationError(
          `${SOURCES_PATH} line ${i + 1} is not valid JSON: ${(exc as Error).message}`,
        );
      }
    }
    return out;
  }

  /** Return the `shapes.ttl` Turtle text (Shapes class), or null if absent. */
  async shapes(): Promise<string | null> {
    if (!this.container.has(SHAPES_PATH)) return null;
    return this.container.readText(SHAPES_PATH);
  }

  /** Return the manifest embedding descriptors (Embeddings class). [] if none. */
  embeddings(): Record<string, unknown>[] {
    return ((this.manifest.raw.embeddings as Record<string, unknown>[] | undefined) ?? []).slice();
  }

  /**
   * Verify each declared signature over the raw `manifest.json` bytes. Offline and
   * fail-closed. Dispatch is by `signatures[].format`: `ed25519` (verified here),
   * the reserved post-quantum formats (recognised but not implemented), and any
   * other value (unsupported).
   */
  async verifySignatures(): Promise<SignatureResult[]> {
    const entries =
      (this.manifest.raw.signatures as Record<string, unknown>[] | undefined) ?? [];
    const manifestBytes = await this.container.read(MANIFEST_PATH);
    const results: SignatureResult[] = [];
    for (const entry of entries) {
      const path = entry.path as string | undefined;
      const fmt = entry.format as string | undefined;
      const result: SignatureResult = {
        path: (path ?? "") as string,
        format: (fmt ?? "") as string,
        verified: false,
      };
      if (!path || !this.container.has(path)) {
        result.error = `signature file missing: ${JSON.stringify(path)}`;
        results.push(result);
        continue;
      }
      const sigBytes = await this.container.read(path);
      if (fmt === "ed25519") {
        const pub = (entry.public_key as string | undefined) ?? "";
        const { verified, error } = verifyEd25519(manifestBytes, sigBytes, pub);
        result.verified = verified;
        if (error) result.error = error;
        result.publicKey = entry.public_key as string | undefined;
      } else if (fmt && (RESERVED_PQC_FORMATS as readonly string[]).includes(fmt)) {
        result.error = `post-quantum format ${JSON.stringify(fmt)} is reserved but not yet implemented`;
      } else {
        result.error = `unsupported signature format: ${JSON.stringify(fmt)}`;
      }
      results.push(result);
    }
    return results;
  }

  /**
   * Generic, vendor-neutral statistics. From the default graph's `@graph`, split
   * `@type: "ccx:Relationship"` (or the bare `Relationship` term) resources —
   * counted as edges — from everything else (entities, counted as nodes). The
   * source count is the number of `sources.jsonl` records. No application schema
   * knowledge.
   */
  async computeStats(): Promise<PackageStats> {
    let nodeCount = 0;
    let edgeCount = 0;

    const defaultEntry = this.manifest.graphs.find((g) => isDefault(g));
    if (defaultEntry) {
      const raw = await this.container.readText(defaultEntry.path);
      let doc: unknown;
      try {
        doc = JSON.parse(raw);
      } catch {
        doc = null;
      }
      const nodes = extractGraphNodes(doc);
      for (const node of nodes) {
        if (isRelationship(node)) edgeCount++;
        else nodeCount++;
      }
    }

    const sources = await this.sources();
    return { nodeCount, edgeCount, sourceCount: sources.length };
  }
}

/** True if a JSON-LD node is typed (CURIE or bare term) as a ccx Relationship. */
function isRelationship(node: Record<string, unknown>): boolean {
  const t = node["@type"];
  const types = Array.isArray(t) ? t : [t];
  return types.some((x) => x === "ccx:Relationship" || x === "Relationship");
}

/** Pull the list of resource nodes out of a JSON-LD document's `@graph`. */
function extractGraphNodes(doc: unknown): Record<string, unknown>[] {
  if (doc === null || typeof doc !== "object") return [];
  const graph = (doc as Record<string, unknown>)["@graph"];
  const arr = Array.isArray(graph) ? graph : Array.isArray(doc) ? doc : [];
  return arr.filter(
    (n): n is Record<string, unknown> =>
      typeof n === "object" && n !== null && !Array.isArray(n),
  );
}

/**
 * Open a `.ccx` package from raw bytes. Unsafe archives (zip bomb, traversal,
 * symlink, bad ZIP) throw here via `Container.load`; a missing, malformed, or
 * schema-invalid `manifest.json` also throws here via `loadManifest`. The
 * mimetype rule is deferred to `validate()` (it is a recoverable validation error,
 * not an open-time rejection).
 */
export async function openPackage(bytes: Uint8Array): Promise<CcxPackage> {
  const container = await Container.load(bytes);
  if (!container.has(MANIFEST_PATH)) {
    throw new CcxValidationError(`missing ${MANIFEST_PATH}`);
  }
  const raw = await container.readText(MANIFEST_PATH);
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch (exc) {
    throw new CcxValidationError(`${MANIFEST_PATH} is not valid JSON: ${(exc as Error).message}`);
  }
  const manifest = loadManifest(data);
  return new CcxPackage(container, manifest);
}
