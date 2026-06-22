import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import JSZip from "jszip";
import { beforeAll, expect, test } from "vitest";
import { verifyEd25519 } from "../src/signing";

const fx = (p: string) => readFileSync(resolve(__dirname, "../../conformance", p));

// Extracted straight from the real app-signed fixture via jszip (this suite does
// NOT depend on the sibling container.ts) — round-tripping against it pins the
// raw-32 -> SPKI-DER wrap.
let manifestBytes: Uint8Array;
let sig: Uint8Array;
let pub: string;

beforeAll(async () => {
  const zip = await JSZip.loadAsync(fx("valid/signed-minimal.ccx"));
  manifestBytes = await zip.file("manifest.json")!.async("uint8array");
  sig = await zip.file("signatures/manifest.sig")!.async("uint8array");
  const manifest = JSON.parse(new TextDecoder().decode(manifestBytes));
  expect(manifest.signatures[0].format).toBe("ed25519");
  pub = manifest.signatures[0].public_key;
});

test("real signed fixture round-trip verifies true", () => {
  const r = verifyEd25519(manifestBytes, sig, pub);
  expect(r.error).toBeUndefined();
  expect(r.verified).toBe(true);
});

test("flipping one manifest byte fails verification", () => {
  const tampered = Uint8Array.from(manifestBytes);
  tampered[0] ^= 0x01; // flip a single bit of the first byte
  const r = verifyEd25519(tampered, sig, pub);
  expect(r.verified).toBe(false);
  expect(r.error).toBeDefined();
});

test("a wrong-length (bogus 16-byte) key fails closed with an error", () => {
  const bogus = Buffer.alloc(16, 0x42).toString("base64"); // 16 bytes, not 32
  const r = verifyEd25519(manifestBytes, sig, bogus);
  expect(r.verified).toBe(false);
  expect(r.error).toMatch(/length 16/);
});
