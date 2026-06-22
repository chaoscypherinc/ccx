import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "vitest";
import { Container } from "../src/container";

const fx = (p: string) => readFileSync(resolve(__dirname, "../../conformance", p));

test("valid core opens; mimetype check passes", async () => {
  const c = await Container.load(fx("valid/core-minimal.ccx"));
  expect(() => c.checkMimetype()).not.toThrow();
  expect(c.has("manifest.json")).toBe(true);
});

test("compressed mimetype rejected (must be STORED)", async () => {
  const c = await Container.load(fx("invalid/compressed-mimetype.ccx"));
  expect(() => c.checkMimetype()).toThrow(/STORED|stored/);
});

test("missing mimetype rejected", async () => {
  const c = await Container.load(fx("invalid/missing-mimetype.ccx"));
  expect(() => c.checkMimetype()).toThrow(/first archive entry/);
});

test("path traversal rejected at load", async () => {
  await expect(Container.load(fx("invalid/path-traversal.ccx"))).rejects.toThrow(/unsafe path/);
});

test("read / readText round-trip on a known entry", async () => {
  const c = await Container.load(fx("valid/core-minimal.ccx"));
  const bytes = await c.read("manifest.json");
  expect(bytes).toBeInstanceOf(Uint8Array);
  expect(bytes.byteLength).toBeGreaterThan(0);
  const text = await c.readText("manifest.json");
  expect(text).toBe(new TextDecoder("utf-8").decode(bytes));
  // manifest.json is JSON; the round-trip must parse and expose the package name.
  const manifest = JSON.parse(text);
  expect(typeof manifest.name).toBe("string");
});

test("reading a missing entry throws CcxValidationError", async () => {
  const c = await Container.load(fx("valid/core-minimal.ccx"));
  await expect(c.read("does-not-exist.json")).rejects.toThrow(/missing entry/);
});
