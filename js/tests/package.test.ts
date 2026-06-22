/**
 * Unit tests for `CcxPackage` / `openPackage` (`src/package.ts`): the open-time
 * vs. validate-time split, the accessors, signature dispatch, and the generic
 * vendor-neutral `computeStats()`.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

import { openPackage, CcxPackage } from "../src/package";
import { CcxSecurityError, CcxValidationError } from "../src/errors";

const dir = resolve(__dirname, "../../conformance");
const fx = (p: string): Uint8Array => readFileSync(resolve(dir, p));
const open = (p: string) => openPackage(fx(p));

describe("openPackage", () => {
  test("opens a valid package and parses the manifest eagerly", async () => {
    const pkg = await open("valid/core-minimal.ccx");
    expect(pkg).toBeInstanceOf(CcxPackage);
    expect(pkg.manifest.ccxVersion).toBe("3.0");
    expect(pkg.manifest.graphs.length).toBeGreaterThan(0);
  });
  test("rejects a missing manifest at open", async () => {
    await expect(open("invalid/missing-manifest.ccx")).rejects.toThrow(CcxValidationError);
  });
  test("rejects a malformed (non-JSON) manifest at open", async () => {
    await expect(open("invalid/malformed-manifest.ccx")).rejects.toThrow(/not valid JSON/);
  });
  test("rejects a schema-invalid manifest at open", async () => {
    await expect(open("invalid/invalid-manifest.ccx")).rejects.toThrow(/schema validation/);
  });
  test("rejects path traversal at open (security)", async () => {
    await expect(open("invalid/path-traversal.ccx")).rejects.toThrow(CcxSecurityError);
  });
  test("does NOT reject a missing mimetype at open (deferred to validate)", async () => {
    const pkg = await open("invalid/missing-mimetype.ccx");
    expect(pkg).toBeInstanceOf(CcxPackage);
  });
});

describe("validate()", () => {
  test("core-minimal => ok, classes=[core], conformanceLevel=core", async () => {
    const r = await (await open("valid/core-minimal.ccx")).validate();
    expect(r.ok).toBe(true);
    expect(r.classes).toEqual(["core"]);
    expect(r.conformanceLevel).toBe("core");
  });
  test("bad-checksum => ok=false with a checksum-mismatch error", async () => {
    const r = await (await open("invalid/bad-checksum.ccx")).validate();
    expect(r.ok).toBe(false);
    expect(r.errors.some((e) => /checksum mismatch/.test(e))).toBe(true);
  });
  test("missing-mimetype => ok=false with the mimetype error (caught, not thrown)", async () => {
    const r = await (await open("invalid/missing-mimetype.ccx")).validate();
    expect(r.ok).toBe(false);
    expect(r.errors.some((e) => /first archive entry/.test(e))).toBe(true);
  });
  test("remote-context => ok=false (remote @context rejected)", async () => {
    const r = await (await open("invalid/remote-context.ccx")).validate();
    expect(r.ok).toBe(false);
    expect(r.errors.some((e) => /remote @context/.test(e))).toBe(true);
  });
});

describe("accessors", () => {
  test("context() parses context.jsonld", async () => {
    const ctx = await (await open("valid/core-minimal.ccx")).context();
    expect(typeof ctx).toBe("object");
  });
  test("graphDocuments() returns declared graphs with parsed docs", async () => {
    const docs = await (await open("valid/core-with-app-graph.ccx")).graphDocuments();
    expect(docs.length).toBe(2);
    expect(docs[0].path.endsWith(".jsonld")).toBe(true);
    expect(docs[0].doc).toBeTypeOf("object");
  });
  test("sources() parses sources.jsonl, [] when absent", async () => {
    expect(await (await open("valid/sources-minimal.ccx")).sources()).toHaveLength(2);
    expect(await (await open("valid/core-minimal.ccx")).sources()).toEqual([]);
  });
  test("shapes() returns Turtle text or null", async () => {
    expect(await (await open("valid/shapes-minimal.ccx")).shapes()).toContain("sh:");
    expect(await (await open("valid/core-minimal.ccx")).shapes()).toBeNull();
  });
  test("embeddings() returns descriptors or []", async () => {
    expect(await (await open("valid/embeddings-minimal.ccx")).embeddings()).toHaveLength(1);
    expect((await open("valid/core-minimal.ccx")).embeddings()).toEqual([]);
  });
  test("assetBytes() returns bytes for a declared asset, throws otherwise", async () => {
    const pkg = await open("valid/embeddings-minimal.ccx");
    const path = pkg.manifest.assets[0].path;
    const bytes = await pkg.assetBytes(path);
    expect(bytes.byteLength).toBeGreaterThan(0);
    await expect(pkg.assetBytes("does/not/exist")).rejects.toThrow(CcxValidationError);
  });
});

describe("verifySignatures (dispatch)", () => {
  test("ed25519 verifies against the real signed fixture", async () => {
    const results = await (await open("valid/signed-minimal.ccx")).verifySignatures();
    expect(results).toHaveLength(1);
    expect(results[0].format).toBe("ed25519");
    expect(results[0].verified).toBe(true);
  });
  test("missing signature file => not verified, reports missing", async () => {
    const results = await (await open("invalid/signed-missing-sig.ccx")).verifySignatures();
    expect(results[0].verified).toBe(false);
    expect(results[0].error).toMatch(/missing/);
  });
});

describe("computeStats (generic, vendor-neutral)", () => {
  test("counts entities vs ccx:Relationship edges in the default graph + sources", async () => {
    const stats = await (await open("valid/core-with-app-graph.ccx")).computeStats();
    // core-with-app-graph default graph has 2 plain entities, no relationships.
    expect(stats.nodeCount).toBe(2);
    expect(stats.edgeCount).toBe(0);
    expect(stats.sourceCount).toBe(0);
  });
  test("source count reflects sources.jsonl records", async () => {
    const stats = await (await open("valid/sources-minimal.ccx")).computeStats();
    expect(stats.sourceCount).toBe(2);
  });
});
