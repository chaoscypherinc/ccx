/** SHA-256 / SHA-512 helpers (base64-encoded digests), matching `src/ccx/checksums.py`. */

import { createHash } from "node:crypto";

const b64 = (algo: string, data: Uint8Array): string =>
  createHash(algo).update(data).digest("base64");

/** Base64-encoded SHA-256 digest of *data*. */
export const sha256b64 = (d: Uint8Array): string => b64("sha256", d);

/** Base64-encoded SHA-512 digest of *data*. */
export const sha512b64 = (d: Uint8Array): string => b64("sha512", d);

/** True iff both digests of *data* match the supplied base64 strings. */
export const verify = (d: Uint8Array, s256: string, s512: string): boolean =>
  sha256b64(d) === s256 && sha512b64(d) === s512;
