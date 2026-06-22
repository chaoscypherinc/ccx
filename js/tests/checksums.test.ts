import { createHash } from "node:crypto";
import { describe, expect, test } from "vitest";
import { sha256b64, sha512b64, verify } from "../src/checksums";

const data = Buffer.from("hello");

// Expected base64 digests computed independently with node:crypto.
const expected256 = createHash("sha256").update(data).digest("base64");
const expected512 = createHash("sha512").update(data).digest("base64");

describe("checksums (base64 digests)", () => {
  test("sha256b64 matches an independent node:crypto digest", () => {
    expect(sha256b64(data)).toBe(expected256);
    // Sanity: base64 of a 32-byte digest is 44 chars (with padding).
    expect(sha256b64(data)).toHaveLength(44);
  });

  test("sha512b64 matches an independent node:crypto digest", () => {
    expect(sha512b64(data)).toBe(expected512);
    // Sanity: base64 of a 64-byte digest is 88 chars (with padding).
    expect(sha512b64(data)).toHaveLength(88);
  });

  test("verify returns true for the correct base64 pair", () => {
    expect(verify(data, expected256, expected512)).toBe(true);
  });

  test("verify returns false if sha256 is wrong", () => {
    const wrong256 = createHash("sha256").update("goodbye").digest("base64");
    expect(verify(data, wrong256, expected512)).toBe(false);
  });

  test("verify returns false if sha512 is wrong", () => {
    const wrong512 = createHash("sha512").update("goodbye").digest("base64");
    expect(verify(data, expected256, wrong512)).toBe(false);
  });

  test("verify returns false if both digests are wrong", () => {
    expect(verify(data, "not-a-digest", "also-wrong")).toBe(false);
  });

  test("works on a raw Uint8Array (not just Buffer)", () => {
    const bytes = new Uint8Array([104, 101, 108, 108, 111]); // "hello"
    expect(sha256b64(bytes)).toBe(expected256);
    expect(sha512b64(bytes)).toBe(expected512);
    expect(verify(bytes, expected256, expected512)).toBe(true);
  });
});
