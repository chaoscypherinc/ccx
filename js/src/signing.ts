/**
 * Offline Ed25519 signature verification for the Signed conformance class.
 *
 * Port-of-record: `src/ccx/signing.py` (`verify_ed25519`). Verification is
 * **offline** (no network at read time) and **fails closed** — any error
 * (bad key, bad length, malformed signature) yields `{ verified: false, error }`.
 *
 * A verified Ed25519 signature proves "signed by the holder of *this* key +
 * unaltered"; the public key travels in the manifest, so binding the key to a
 * real identity is the verifier's job (pin/trust the key out-of-band, like
 * SSH/minisign).
 *
 * **Node nuance:** the manifest `public_key` is base64 of the **raw 32-byte**
 * Ed25519 key. Python's `cryptography` accepts raw bytes directly; Node's
 * `crypto.createPublicKey` does NOT — it needs DER/PEM/JWK. We wrap the raw 32
 * bytes in the fixed Ed25519 SPKI DER prefix (`302a300506032b6570032100`, 12
 * bytes) and import as `spki`/`der`, then `verify(null, ...)` (null algorithm
 * => Ed25519 inferred from the key).
 *
 * The reserved post-quantum formats (FIPS 204 ML-DSA / FIPS 205 SLH-DSA) are
 * recognised by the package-level signed-class dispatch (see `package.ts`) but
 * are not implemented here; `RESERVED_PQC_FORMATS` is re-exported so that
 * dispatch can reference the canonical list.
 */

import { createPublicKey, verify as nodeVerify } from "node:crypto";
import { RESERVED_PQC_FORMATS } from "./constants";

export { RESERVED_PQC_FORMATS };

/** Fixed Ed25519 SubjectPublicKeyInfo DER prefix (12 bytes) for a raw 32-byte key. */
const SPKI_ED25519_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

/**
 * Verify a detached Ed25519 signature over `message`. Fails closed: any failure
 * (invalid base64, wrong key length, key-import error, or non-verifying
 * signature) returns `{ verified: false, error }`.
 *
 * @param message    the signed bytes (the manifest bytes for a CCX package)
 * @param signature  the detached signature (`signatures/manifest.sig`)
 * @param publicKeyB64 base64 of the raw 32-byte Ed25519 public key (from the manifest)
 */
export function verifyEd25519(
  message: Uint8Array,
  signature: Uint8Array,
  publicKeyB64: string,
): { verified: boolean; error?: string } {
  let key;
  try {
    const raw = Buffer.from(publicKeyB64, "base64");
    if (raw.length !== 32) {
      return { verified: false, error: `invalid public key length ${raw.length}` };
    }
    key = createPublicKey({
      key: Buffer.concat([SPKI_ED25519_PREFIX, raw]),
      format: "der",
      type: "spki",
    });
  } catch (e) {
    return { verified: false, error: `invalid public key: ${(e as Error).message}` };
  }
  try {
    // null algorithm => Ed25519 is inferred from the key type.
    const ok = nodeVerify(null, message, key, signature);
    return ok ? { verified: true } : { verified: false, error: "signature does not verify" };
  } catch (e) {
    return { verified: false, error: `verification error: ${(e as Error).message}` };
  }
}
