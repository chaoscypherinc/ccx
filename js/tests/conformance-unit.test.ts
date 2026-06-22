/**
 * Unit tests for the four conformance-class checkers (`src/conformance.ts`),
 * driven against the real conformance fixtures. Each returns `{ present, issues }`.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

import { CHECKERS, checkSources, checkShapes, checkEmbeddings, checkSigned } from "../src/conformance";
import { openPackage } from "../src/package";

const dir = resolve(__dirname, "../../conformance");
const fx = (p: string): Uint8Array => readFileSync(resolve(dir, p));
const open = (p: string) => openPackage(fx(p));

describe("CHECKERS ordering", () => {
  test("is [sources, shapes, embeddings, signed]", () => {
    expect(CHECKERS.map(([name]) => name)).toEqual(["sources", "shapes", "embeddings", "signed"]);
  });
});

describe("checkSources", () => {
  test("present + clean on a Sources package", async () => {
    const r = await checkSources(await open("valid/sources-minimal.ccx"));
    expect(r.present).toBe(true);
    expect(r.issues).toEqual([]);
  });
  test("absent (not present, no issues) on a core-only package", async () => {
    const r = await checkSources(await open("valid/core-minimal.ccx"));
    expect(r.present).toBe(false);
    expect(r.issues).toEqual([]);
  });
});

describe("checkShapes", () => {
  test("present + clean on the Shapes fixture (lightweight Turtle check)", async () => {
    const r = await checkShapes(await open("valid/shapes-minimal.ccx"));
    expect(r.present).toBe(true);
    expect(r.issues).toEqual([]);
  });
  test("absent on a core-only package", async () => {
    const r = await checkShapes(await open("valid/core-minimal.ccx"));
    expect(r.present).toBe(false);
  });
});

describe("checkEmbeddings", () => {
  test("present + clean when the included sidecar is a declared, present asset", async () => {
    const r = await checkEmbeddings(await open("valid/embeddings-minimal.ccx"));
    expect(r.present).toBe(true);
    expect(r.issues).toEqual([]);
  });
  test("absent when no embeddings descriptors are declared", async () => {
    const r = await checkEmbeddings(await open("valid/core-minimal.ccx"));
    expect(r.present).toBe(false);
  });
});

describe("checkSigned", () => {
  test("present + clean when a signature verifies", async () => {
    const r = await checkSigned(await open("valid/signed-minimal.ccx"));
    expect(r.present).toBe(true);
    expect(r.issues).toEqual([]);
  });
  test("absent when no signatures are declared", async () => {
    const r = await checkSigned(await open("valid/core-minimal.ccx"));
    expect(r.present).toBe(false);
  });
});
