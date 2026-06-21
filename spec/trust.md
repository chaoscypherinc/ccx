# CCX 3.0 — Trust and Integrity

This document is the normative home for the CCX **trust and integrity model**:
the digest algorithms and encoding that protect every declared file (Core), the
licensing declarations that describe how contained material may be used, and the
manifest signatures that authenticate a package (the Signed class).

> Normative keywords ("MUST", "MUST NOT", "SHOULD", "MAY", "OPTIONAL", etc.) are
> to be interpreted as described in RFC 2119 / RFC 8174 (see `ccx-3.0.md` §1),
> and only when they appear in all capitals. Text without these keywords is
> explanatory and non-normative.

> Implementation status: checksums are Core (enforced). ed25519 signing + offline
> verification are enforced by the reference reader/writer (`PackageBuilder.sign`,
> `CCXPackage.verify_signatures`); the `sigstore` and post-quantum formats are
> recognised by the verify dispatch (sigstore delegated to the optional
> `signed-sigstore` extra; ML-DSA/SLH-DSA reserved); per-source/graph licensing is
> spec + fixture only.

Cross-references are to sibling files in `spec/`. The fixture suite is in
`conformance/` at the repository root.

---

## 1. Scope and relationship to other documents

CCX layers three distinct guarantees onto a package:

1. **Integrity** (Section 2) — proof that the bytes a reader processes are the
   bytes the manifest describes. This is a **Core** requirement: it applies to
   every CCX package regardless of conformance class.
2. **Licensing** (Section 3) — an honest, machine-readable declaration of the
   terms under which the package and its constituent material may be used.
3. **Authenticity** (Section 4) — proof of *who* produced a package and that its
   manifest has not been altered since. This is a requirement of the **Signed**
   conformance class only.

This document is the authoritative definition of the digest algorithms and their
encoding. Where `ccx-3.0.md` §5 and `manifest.md` §3.2 refer to "the integrity
model and digest algorithms" or "the digest encoding," they refer to Section 2
of this document. Where this document and `manifest.schema.json` describe the
same structure, the two MUST agree; the resolution rule of `manifest.md` §1
governs any divergence.

---

## 2. Integrity (Core class)

### 2.1 Dual digests are mandatory

Every graph entry declared in the manifest's `graphs` array and every asset entry
declared in its `assets` array MUST carry **both** a `sha256` digest and a
`sha512` digest. Neither digest is optional and neither substitutes for the
other: a declared entry that is missing either field makes the package invalid.

- The `sha256` field MUST be the SHA-256 hash, computed per FIPS 180-4, of the
  entry's exact bytes.
- The `sha512` field MUST be the SHA-512 hash, computed per FIPS 180-4, of the
  same exact bytes.

"Exact bytes" means the uncompressed content of the corresponding ZIP entry as it
is stored in the archive, with no normalization, re-encoding, or transformation
of any kind. The digest is computed over those bytes verbatim.

### 2.2 Encoding

Each digest MUST be encoded as **standard base64** (RFC 4648 §4, the alphabet
using `+` and `/`, with `=` padding) of the **raw** hash output — that is, the
32 raw bytes of a SHA-256 digest or the 64 raw bytes of a SHA-512 digest. The
encoding is identical for both algorithms; only the input hash differs.

Producers MUST NOT use hexadecimal, base64url (the URL-safe `-`/`_` alphabet), or
unpadded base64 for these fields. A correctly encoded `sha256` value is 44
characters long (including one `=` of padding) and a correctly encoded `sha512`
value is 88 characters long; readers MAY use these lengths as a cheap sanity
check but MUST still perform the full byte comparison of Section 2.3.

> Note (informative): hexadecimal SHA-256 is used elsewhere in the format for
> *content-addressed asset paths* — naming a file by its content. That hex
> encoding is a naming convention and is distinct from the base64 **integrity
> digests** specified here. The two MUST NOT be conflated.

### 2.3 Reader verification is mandatory

Before relying on the contents of any declared graph or asset, a reader MUST:

1. recompute the SHA-256 and SHA-512 digests of the entry's exact bytes;
2. base64-encode each per Section 2.2; and
3. compare each result against the corresponding `sha256` and `sha512` value
   declared in the manifest.

A reader MUST verify **both** digests for **every** declared file. A reader MUST
treat any of the following as a **fatal** error and MUST refuse to expose the
package's dataset as valid:

- a declared `sha256` that does not equal the recomputed, re-encoded SHA-256
  digest of the entry's bytes;
- a declared `sha512` that does not equal the recomputed, re-encoded SHA-512
  digest of the entry's bytes;
- a `graphs[]` or `assets[]` entry that omits either digest field.

A reader MUST NOT accept a match on one digest as sufficient when the other does
not match, and MUST NOT skip verification for entries it does not otherwise
intend to parse: integrity is verified for the whole declared file set, not only
for the graphs the reader loads.

This requirement is the normative basis for the Core conformance requirement on
checksums (`conformance.md` §2.1, requirement 7) and for the cross-entry
constraint in `manifest.md` §3.2.

### 2.4 Relationship to container hardening

Integrity verification is independent of, and additional to, the container
hardening required of every reader (decompression-bomb bounds, path-traversal and
absolute-path rejection, symlink-escape rejection, and the prohibition on remote
context fetching). Those defenses are defined in `ccx-3.0.md` §6 and MUST be
applied *before* any entry is inflated or hashed. Passing digest verification
does not waive any container-hardening requirement, and vice versa.

---

## 3. Licensing

### 3.1 Package-level license (mandatory declaration)

A package MUST declare a top-level `license` field in its manifest whose value is
a valid **SPDX license identifier** (for example `"CC-BY-4.0"`, `"Apache-2.0"`,
or `"CC0-1.0"`). The package-level `license` states the terms under which the
package as a whole is offered and is the **default** license for every contained
graph, asset, and source record that does not declare its own.

A reader SHOULD surface the declared license to consuming applications. The
absence or malformation of `license` compromises honest reuse but not Core
integrity; consistent with `ccx-3.0.md` §5, a reader SHOULD surface a missing or
non-SPDX `license` as a warning rather than a fatal error.

### 3.2 Per-graph and per-source overrides

A bundle frequently mixes material under different terms — for example,
CC-BY-licensed reference data alongside a CC0 application overlay, or cited source
documents whose licenses differ from the package's own. To describe such a bundle
**honestly**, a package MAY declare per-entry `license` overrides:

- a `graphs[]` entry MAY carry its own `license` (an SPDX identifier) that governs
  that graph only;
- an `assets[]` entry MAY carry its own `license` that governs that asset only;
- a source record MAY carry its own `license`, as detailed in `sources.md`.

Each override, where present, MUST be a valid SPDX license identifier and applies
**only** to the entry that carries it. Where a graph, asset, or source declares no
`license`, the package-level `license` of Section 3.1 applies to it.

These overrides are **higher-class** fields: they are specified here and in
`manifest.md` §5.4, accommodated by `manifest.schema.json`, and exercised by
conformance fixtures, but carry no reference-library behavior yet (see the
implementation-status note above). A reader MUST ignore an override it does not
understand rather than rejecting the package, and MUST NOT silently widen an
entry's terms: an absent override means "inherit the package license," never "no
license."

### 3.3 Effective license resolution (informative)

The effective license of any single graph, asset, or source is therefore: its own
`license` if present; otherwise the package-level `license`. Tools that compute an
aggregate license for a bundle SHOULD treat the set of effective per-entry
licenses as authoritative, rather than assuming the package-level `license`
covers every entry uniformly.

---

## 4. Authenticity (Signed class)

### 4.1 Overview

Integrity (Section 2) proves that a package's bytes match its manifest, but it
says nothing about *who* produced the manifest. **Authenticity** closes that gap
with one or more cryptographic signatures over the manifest. Signing is a
requirement of the **Signed** conformance class (`conformance.md` §2.5) and is
OPTIONAL at every lower class.

### 4.2 What is signed, and why signing the manifest suffices

A CCX signature covers the **manifest** (`manifest.json`). It does not separately
sign each graph or asset. This is sufficient — and deliberate — because the
manifest already carries a verified `sha256` **and** `sha512` digest for every
declared file (Section 2). A signature therefore binds the signer to the exact
digest of every declared entry. Once a reader has (a) verified the signature over
the manifest and (b) verified each declared file against its manifest digests, the
signature **transitively** authenticates the entire declared package: no declared
graph or asset can be altered without invalidating a digest, and no digest can be
altered without invalidating the signature.

It follows that signature verification is meaningful only in conjunction with the
Section 2 digest checks. A reader MUST NOT treat a valid manifest signature as a
substitute for digest verification; both checks are required for a Signed-class
package to be considered authentic and intact.

### 4.3 Storage and declaration

A package conforming to the Signed class:

- MUST store its signature material under the `signatures/` directory in the
  archive (see `ccx-3.0.md` §3.3, which reserves this directory for non-Core
  classes); and
- MUST declare each signature in a top-level manifest `signatures` array.

Each element of the `signatures` array is an object that MUST carry:

| Field | Type | Meaning |
|-------|------|---------|
| `path` | string | The ZIP entry (under `signatures/`) holding the signature material. MUST exist in the archive (`manifest.md` §3.1). |
| `format` | string | The signature format identifier (Section 4.6). A reader MUST ignore a signature whose `format` it does not understand rather than treating it as a verification failure. |

Formats MAY define additional fields. The `ed25519` format carries a `public_key`
field — the base64-encoded raw Ed25519 public key used to verify the signature.

**The signature file is not a checksum-protected declared entry.** Unlike graphs
and assets, a `signatures[].path` file MUST NOT be required to carry `sha256` /
`sha512` digests in the manifest: the manifest is the *signed payload*, so
committing the signature's own digest inside it would be circular. The signature
file needs no separate checksum — any alteration to it causes verification
(Section 4.4) to fail. A reader MUST verify the signature over the manifest bytes,
not over a digest of the signature file.

What is signed is the **exact bytes of `manifest.json`** as stored in the archive
(no normalization or re-serialization). This is why the format-identifying metadata
(`format`, and for `ed25519` the `public_key`) lives *inside* the manifest while the
signature itself lives *outside* it, under `signatures/`.

### 4.4 Reader obligations

Whether a reader verifies signatures depends on the conformance class it claims:

- A reader that **claims the Signed class** MUST verify at least one declared
  signature. If at least one declared signature in a format the reader understands
  verifies successfully over the manifest, the package's authenticity is
  established. If **no** declared signature verifies — because every signature
  fails, every signature is in an unrecognized format, the `signatures` array is
  empty, or the `signatures/` directory is absent or empty — the reader MUST treat
  the package as a **fatal** error at the Signed class and MUST NOT report it as
  conforming to the Signed class.
- A reader that **does NOT claim the Signed class** MAY ignore signatures
  entirely. Such a reader MUST NOT treat the presence of unverified or
  unverifiable signature material as a failure: signing is a higher-class feature,
  and a Core reader's obligations are exactly those of Section 2 plus the
  container and licensing rules above.

In no case may a reader treat the mere *presence* of a `signatures` entry as proof
of authenticity. Authenticity is established only by successful verification as
described here, and only in addition to the Section 2 digest checks
(`manifest.md` §9 makes the same point from the manifest's side).

### 4.5 Multiple signatures

A package MAY carry more than one signature — for example, signatures from
multiple signers, or in multiple formats. For a Signed-class reader, the package
is authentic if **at least one** declared signature verifies. A producer that
wishes to require agreement among several signers MUST express that policy outside
this specification; CCX defines the verification of individual signatures, not
multi-party signing policy. (A hybrid classical + post-quantum policy is one such
case; see Section 4.6.)

### 4.6 Signature formats, crypto-agility, and post-quantum readiness

`format` is an **open discriminator** and `signatures` is a **list** — together
these make CCX signing crypto-agile and able to carry **hybrid** (multi-scheme)
signatures over the same manifest. The defined and reserved formats are:

- **`ed25519`** *(defined; reference-implemented).* A detached Ed25519 signature
  (RFC 8032) over the manifest bytes; the base64 raw public key travels in
  `public_key`. Fully offline, no PKI. A verified `ed25519` signature proves "the
  holder of *this* key signed these exact manifest bytes" — binding the key to a
  real-world identity is the verifier's responsibility (pin or otherwise trust the
  key out-of-band, as with SSH or minisign).
- **`sigstore`** *(defined; verification delegated).* An identity-bound Sigstore
  bundle (an OIDC identity certified by Fulcio, logged in Rekor), carried at `path`.
  It MUST be verifiable **offline** against a pinned Sigstore trusted root — a CCX
  reader MUST NOT reach the network at read time (`ccx-3.0.md` §6). Suited to
  public-hub distribution where identities, not pinned keys, anchor trust.
- **`ml-dsa-*`, `slh-dsa-*`** *(RESERVED).* The NIST post-quantum signature
  standards (FIPS 204 ML-DSA, FIPS 205 SLH-DSA). Reserved format values, not yet
  defined in detail or reference-implemented; the open `format` discriminator means
  adding them is not a format change.

**Post-quantum posture.** Ed25519, like all elliptic-curve schemes, is broken by a
large quantum computer, so it is the *transitional* scheme, not the end state. CCX
is post-quantum-*ready* by construction: (a) the integrity digests are SHA-256 and
SHA-512, which retain roughly 128-bit and 256-bit security against Grover's
algorithm and need no change; (b) `format` agility lets a post-quantum scheme be
added without altering the format; and (c) because `signatures` is a list, a package
MAY carry a **hybrid** classical + post-quantum pair (e.g. `ed25519` + `ml-dsa-65`),
which a verifier policy MAY require to both verify — the recommended posture during
the transition. CCX MUST NOT make Ed25519, or any single classical scheme, a
mandatory part of the Signed class.

---

## 5. Cross-references

- `ccx-3.0.md` — container model, the reader contract (§5) and security
  hardening (§6) that integrity verification complements; reserves `signatures/`.
- `manifest.md` — the manifest structure: `sha256`/`sha512` on every entry
  (§3.2, §6, §7), the `license` field and overrides (§5.4), and the `signatures`
  array (§9).
- `conformance.md` — normative class membership: Core checksums (§2.1) and the
  Signed class (§2.5), including the Sigstore signature-format requirement.
- `sources.md` — per-source `license` overrides and source records.
- `manifest.schema.json` — the authoritative structural schema these fields
  validate against.
