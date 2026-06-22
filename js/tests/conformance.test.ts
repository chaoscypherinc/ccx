/**
 * Cross-implementation verdict-parity suite — the acceptance gate.
 *
 * For every conformance fixture, the TypeScript reader's verdict MUST match the
 * Python reference reader (`src/ccx/`), the oracle. The matrix below was confirmed
 * by running the Python reader over `conformance/{valid,invalid}/*.ccx`:
 *
 *   python -c "import ccx; ... open_package(p).validate()"
 *
 * Verdict per fixture (Python oracle):
 *   VALID                -> validate().ok === true, with the exact `classes`.
 *   REJECT-AT-OPEN       -> openPackage() throws.
 *   REJECT-AT-VALIDATE   -> openPackage() succeeds; validate().ok === false.
 *
 * NOTE vs the plan stub: `missing-mimetype` is REJECT-AT-VALIDATE, not
 * REJECT-AT-OPEN. The Python oracle returns ok=false (error: "first archive entry
 * must be 'mimetype'") rather than throwing at open — the mimetype rule is a
 * caught, accumulated validation error, never an open-time rejection. The matrix
 * is corrected to match the oracle; assertions are never weakened to match the TS
 * reader.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

import { openPackage } from "../src/index";

const dir = resolve(__dirname, "../../conformance");
const fx = (p: string): Uint8Array => readFileSync(resolve(dir, p));

/** Valid fixtures -> the exact set of conformance classes the oracle grants. */
const VALID: Record<string, string[]> = {
  "core-minimal": ["core"],
  "core-with-app-graph": ["core"],
  "sources-minimal": ["core", "sources"],
  "sources-inline-chunk": ["core", "sources"],
  "sources-only": ["core", "sources"],
  "embeddings-minimal": ["core", "embeddings"],
  "signed-minimal": ["core", "signed"],
  "shapes-minimal": ["core", "shapes"],
};

/** Invalid fixtures the oracle rejects at open (openPackage throws). */
const INVALID_REJECT_AT_OPEN = [
  "path-traversal",
  "missing-manifest",
  "malformed-manifest",
  "invalid-manifest",
];

/** Invalid fixtures the oracle opens but reports ok=false from validate(). */
const INVALID_REJECT_AT_VALIDATE = [
  "missing-mimetype",
  "compressed-mimetype",
  "bad-checksum",
  "signed-missing-sig",
  "remote-context",
  "remote-context-file",
  "corrupt-context",
];

describe("valid fixtures: ok=true with exact classes (Python parity)", () => {
  for (const [name, classes] of Object.entries(VALID)) {
    test(name, async () => {
      const pkg = await openPackage(fx(`valid/${name}.ccx`));
      const r = await pkg.validate();
      expect(r.ok).toBe(true);
      expect([...r.classes].sort()).toEqual([...classes].sort());
      expect(r.conformanceLevel).toBe("core");
      expect(r.errors).toEqual([]);
    });
  }
});

describe("invalid fixtures rejected at open (Python parity)", () => {
  for (const name of INVALID_REJECT_AT_OPEN) {
    test(`${name} (open throws)`, async () => {
      await expect(openPackage(fx(`invalid/${name}.ccx`))).rejects.toThrow();
    });
  }
});

describe("invalid fixtures rejected at validate (Python parity)", () => {
  for (const name of INVALID_REJECT_AT_VALIDATE) {
    test(`${name} (open ok, validate ok=false)`, async () => {
      const pkg = await openPackage(fx(`invalid/${name}.ccx`));
      const r = await pkg.validate();
      expect(r.ok).toBe(false);
      expect(r.errors.length).toBeGreaterThan(0);
      expect(r.conformanceLevel).toBeNull();
      expect(r.classes).toEqual([]);
    });
  }
});
