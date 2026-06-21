# CCX 3.0 — Conformance

This document is normative. Keywords **MUST**, **MUST NOT**, **REQUIRED**,
**SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**,
and **OPTIONAL** are interpreted as described in RFC 2119 and RFC 8174.

Cross-references are to sibling files in `spec/`. The fixture suite is in
`conformance/` at the repository root.

> Implementation status: Core, Sources, Shapes, and Embeddings are enforced by the
> reference reader (`validate()` reports the satisfied classes in
> `ValidationReport.classes`) and are fixture-backed. Signed is enforced for the
> `ed25519` format (offline sign + verify); the `sigstore` format is recognised but
> delegated to the optional `signed-sigstore` extra, and post-quantum formats are
> reserved.

---

## 1. Purpose

This document defines:

1. Five **conformance classes** that partition the feature surface of CCX 3.0.
2. The normative **membership rules** each class imposes on a package.
3. The **conformance-claim model** for implementations (readers and writers).
4. The **fixture map** linking each class to its canonical valid and invalid test packages.

A package is said to *conform* to a class if and only if it satisfies every
normative requirement of that class and every class it builds upon.

---

## 2. Conformance Classes

CCX 3.0 defines five conformance classes. The classes are **strictly additive**:
each higher class inherits every requirement of the classes below it and adds
new normative requirements on top. A package that satisfies a higher class
automatically satisfies all lower classes.

The classes, in ascending order of capability, are:

| # | Class name | Short identifier |
|---|------------|-----------------|
| 1 | Core | `core` |
| 2 | Core + Sources | `sources` |
| 3 | Embeddings | `embeddings` |
| 4 | Shapes | `shapes` |
| 5 | Signed | `signed` |

### 2.1 Class 1 — Core

**Membership rule.** A package MUST satisfy all of the following to conform to
the Core class:

1. **MIME type entry.** The first entry in the ZIP archive MUST be the file
   `mimetype`, stored (not deflated), and its content MUST be the exact US-ASCII
   byte sequence `application/vnd.ccx+zip` with no trailing whitespace or
   newline. Readers MUST reject a package in which this entry is absent, is not
   the first archive member, or uses any compression method other than `STORED`.

2. **Schema-valid manifest.** The archive MUST contain a file named
   `manifest.json` at the root. This file MUST be valid JSON and MUST validate
   against the normative JSON Schema published at
   `src/ccx/schemas/manifest.schema.json`. Readers MUST reject a package whose
   `manifest.json` is absent, is not parseable as JSON, or fails schema
   validation.

3. **Bundled JSON-LD context.** The archive MUST contain a file named
   `context.jsonld` at the root. This file MUST be a valid JSON-LD context
   document. The context MUST be read from the archive; readers MUST NOT fetch
   it from a remote URI at read time. The `manifest.json` `@context` field MUST
   reference only the bundled context (by relative path or by the canonical CCX
   context IRI — never by an arbitrary HTTP URL). Readers MUST reject a package
   in which `context.jsonld` is absent, is not parseable, or in which the
   manifest references a remote context.

4. **First-class payload: the `knowledge` default graph.** The archive MUST
   contain at least one JSON-LD file that constitutes the `knowledge` default
   graph as described in `knowledge.md`. This file MUST be resolvable from the
   manifest's graph registry. (For an à-la-carte **sources-only** package this graph
   is present but its `@graph` is empty; the first-class payload is then
   `sources.jsonl`.)

5. **Namespaced named graphs.** Any additional named graphs carried by the
   package MUST follow the naming convention defined in `ccx-3.0.md` §4: each is
   declared in the manifest graph registry by a `namespace` and a `name`
   (written `<namespace>.<contents>`), with the `ccx` namespace reserved for
   standard-defined graphs. A reader maps each non-default graph to a named graph
   derived from its `namespace`/`name`.

6. **Declared assets.** Every file under `assets/` that the package relies on
   MUST be registered in the manifest's asset registry with its `path`,
   `media_type`, and checksums (requirement 7). Content-addressing
   (`assets/sha256/<hex>`) is a convention of the Sources and Embeddings classes,
   not a Core requirement.

7. **Verified checksums.** Every file registered in the manifest MUST carry both
   a `sha256` and a `sha512` digest, base64-encoded per `trust.md` §2.2. Readers
   MUST verify both digests against the corresponding file content and MUST
   reject a package in which any checksum does not match.

The Core class has no dependency on any higher class. A Core-only package is a
complete, self-contained, independently useful artifact.

### 2.2 Class 2 — Core + Sources

**Membership rule.** A package MUST satisfy all Core requirements and, in
addition, all of the following:

1. **`sources.jsonl` present and valid.** The archive MUST contain a file named
   `sources.jsonl` at the root. Each line MUST be a valid JSON object conforming
   to the Sources record schema defined in `sources.md`. Empty files (zero
   records) are permitted only when explicitly documented by the producer; in
   practice a Sources-class package SHOULD contain at least one source record.

2. **Per-source media mode.** Each source's media mode MUST be declared as
   `source_mode`, one of `embedded`, `referenced`, or `derived-only` — on the
   source's manifest asset entry when an original-bytes asset is present,
   otherwise on the source record in `sources.jsonl`. `embedded` ships the
   original bytes as a checksummed asset; `referenced` ships only a locator
   (URL/DOI) plus checksum and metadata; `derived-only` ships only extracted
   text/chunks/citations and no original. See `sources.md` and `manifest.md`.

3. **Extraction provenance.** Each source record SHOULD carry an `extractedBy`
   field identifying the tool or process used to derive knowledge from the
   source, and SHOULD carry a timestamp (`extractedAt`).

4. **Citation anchors.** Where a source record identifies a specific passage,
   segment, or location within a source document, it MUST use W3C Web Annotation
   selector syntax and/or Media Fragments URI syntax to express the citation
   anchor, as specified in `sources.md` §Citation Anchors.

### 2.3 Class 3 — Embeddings

**Membership rule.** A package MUST satisfy all Core requirements and, in
addition, all of the following:

1. **Embedding descriptor in the manifest.** The manifest MUST include an
   `embeddings` block that conforms to the embedding descriptor schema defined
   in `embeddings.md`. The descriptor MUST name the model, dimensionality, and
   encoding format.

2. **Content-addressed vector sidecar(s).** Each embedding file referenced by
   the descriptor MUST be present in `assets/` and MUST be registered in the
   manifest's asset map with a verified checksum (inheriting the Core checksum
   requirement). The sidecar format MUST be one of the formats enumerated in
   `embeddings.md` §Sidecar Formats.

3. **Embedding provenance.** The descriptor MUST record the model identifier
   (name and version, or a resolvable model card IRI) used to compute the
   vectors, so that consumers can detect staleness when a model is updated.

### 2.4 Class 4 — Shapes

**Membership rule.** A package MUST satisfy all Core requirements and, in
addition, all of the following:

1. **Valid SHACL shapes file.** The archive MUST contain a file named
   `shapes.ttl` at the root. This file MUST be valid Turtle syntax and MUST be
   a syntactically and structurally valid SHACL shapes graph as defined by the
   W3C SHACL specification.

2. **Custom vocabulary coverage.** The `shapes.ttl` MUST provide at least one
   `sh:NodeShape` or `sh:PropertyShape` describing vocabulary terms or node
   types that are specific to this package and are not already covered by the
   core CCX vocabulary in `vocabulary.md`.

3. **Manifest declaration.** The manifest MUST declare the presence of
   `shapes.ttl` in the shapes registry as specified in `shapes.md`.

### 2.5 Class 5 — Signed

**Membership rule.** A package MUST satisfy all Core requirements and, in
addition, all of the following:

1. **Signature directory present.** The archive MUST contain a directory entry
   `signatures/`.

2. **Verifiable signature over the manifest.** The `signatures/` directory MUST
   contain at least one signature bundle that covers the canonical serialization
   of `manifest.json`. The signature format MUST follow the Sigstore bundle
   format as described in `trust.md` §Signature Format.

3. **Signature verifiability.** A reader implementing the Signed class MUST be
   able to verify the signature against the declared signing identity without
   network access to any resource not already present in the package, or against
   a Sigstore transparency log using the standard Sigstore verification protocol.
   A package in which the `signatures/` directory is present but empty, or
   contains a bundle that fails verification, MUST be treated as invalid at the
   Signed class level.

---

## 3. Conformance-Claim Model

### 3.1 Implementation claims

An implementation — whether a reader, a writer, or a combined tool — declares
conformance by listing the highest class it fully supports for each of its roles.
Because the classes are strictly additive, supporting a higher class implies
support for all lower classes.

An implementation MAY claim support for a subset of classes that is not a
contiguous prefix (for example, Core + Shapes, without Sources or Embeddings),
provided that the declared classes are each fully satisfied. Such a claim is
honest and complete.

**"Core only" is a complete, honest conformance claim.** It indicates that the
implementation correctly reads or writes packages satisfying all Core
requirements and makes no claim about higher classes.

### 3.2 Reader vs. writer conformance

- A **conformant reader** at class _C_ MUST correctly parse and validate all
  normative requirements of class _C_ and MUST reject packages that violate any
  of those requirements.
- A **conformant writer** at class _C_ MUST produce packages that satisfy all
  normative requirements of class _C_ and MUST NOT produce packages that violate
  any of those requirements.
- An implementation that is both a reader and a writer MUST satisfy both sets of
  obligations for each declared class.

### 3.3 Reference implementation status

The reference reader and writer (`ccx-format`, `import ccx`) enforce **Core,
Core + Sources, Embeddings, Shapes, and Signed (ed25519)** — `validate()` reports
the satisfied classes in `ValidationReport.classes`, with writer support for each.
Sigstore signature verification is delegated to the optional `signed-sigstore`
extra; post-quantum signature formats are reserved.

---

## 4. Fixture Map

The `conformance/` directory contains canonical test packages used to
mechanically verify conformance. Each package is a `.ccx` archive that either
conforms to the specified class (`valid/`) or deliberately violates a single
normative requirement (`invalid/`).

Implementations SHOULD pass all valid fixtures without error and SHOULD reject
all invalid fixtures with an appropriate diagnostic.

### 4.1 Core fixtures

| Status | Path | What it tests |
|--------|------|---------------|
| Valid | `conformance/valid/core-minimal.ccx` | Minimal package satisfying every Core requirement. |
| Valid | `conformance/valid/core-with-app-graph.ccx` | Core package with an additional application-defined named graph. |
| Invalid | `conformance/invalid/bad-checksum.ccx` | A declared SHA-256 checksum does not match the file content. |
| Invalid | `conformance/invalid/missing-mimetype.ccx` | The `mimetype` entry is absent from the archive. |
| Invalid | `conformance/invalid/missing-manifest.ccx` | `manifest.json` is absent from the archive. |
| Invalid | `conformance/invalid/invalid-manifest.ccx` | `manifest.json` is present and parseable but fails JSON Schema validation. |
| Invalid | `conformance/invalid/malformed-manifest.ccx` | `manifest.json` is not parseable as JSON. |
| Invalid | `conformance/invalid/remote-context.ccx` | The manifest `@context` references a remote HTTP URL instead of the bundled context. |
| Invalid | `conformance/invalid/remote-context-file.ccx` | `context.jsonld` contains a remote `@import` or remote term IRI that triggers a fetch. |
| Invalid | `conformance/invalid/corrupt-context.ccx` | `context.jsonld` is present but not parseable as valid JSON-LD. |
| Invalid | `conformance/invalid/path-traversal.ccx` | An archive entry uses a path that escapes the package root (e.g. `../../../etc/passwd`). |
| Invalid | `conformance/invalid/compressed-mimetype.ccx` | `mimetype` is first but DEFLATED instead of STORED (§3.2 requires STORED). |

### 4.2 Core + Sources fixtures

| Status | Path | What it tests |
|--------|------|---------------|
| Valid | `conformance/valid/sources-minimal.ccx` | Minimal Core + Sources package: a `sources.jsonl` record, a content-addressed extracted-text asset, and a `source_mode` on that asset. |
| Valid | `conformance/valid/sources-inline-chunk.ccx` | Core + Sources with an inline-`content` chunk (the graduated fallback; no text asset) + chunking provenance. |
| Valid | `conformance/valid/sources-only.ccx` | À-la-carte sources-only package: an empty `knowledge` graph + `sources.jsonl`. |

> Citation-anchor validity is a Sources-class reader concern. The Core reference
> reader does not parse `sources.jsonl` anchors, so no Core-rejection fixture is
> provided for malformed anchors; a Sources-class implementation SHOULD validate
> anchors against its own fixtures.

### 4.3 Embeddings fixtures

| Status | Path | What it tests |
|--------|------|---------------|
| Valid | `conformance/valid/embeddings-minimal.ccx` | Minimal Embeddings package with a conformant embedding descriptor and one content-addressed vector sidecar. |

### 4.4 Shapes fixtures

| Status | Path | What it tests |
|--------|------|---------------|
| Valid | `conformance/valid/shapes-minimal.ccx` | Minimal Shapes package with a valid SHACL `shapes.ttl` describing at least one custom node shape. |

### 4.5 Signed fixtures

| Status | Path | What it tests |
|--------|------|---------------|
| Valid | `conformance/valid/signed-minimal.ccx` | Minimal Signed package: a real **ed25519** detached signature over the manifest, declared in `signatures` with the public key. The reference reader verifies it offline and grants the Signed class. |
| Invalid | `conformance/invalid/signed-missing-sig.ccx` | The manifest declares a `signatures/manifest.sig` asset that is absent from the archive — rejected by the Core declared-path-exists rule. |

---

## 5. Relationship to Other Spec Documents

- `ccx-3.0.md` — normative container model, reader security contract, and ZIP
  layout rules that underpin Core requirements 1–5.
- `manifest.md` — the full manifest schema; normative for Core requirements 2
  and 6.
- `knowledge.md` — the default graph contract; normative for Core requirement 4.
- `vocabulary.md` — the `ccx:` term vocabulary referenced in §2.4.
- `sources.md` — normative for the Core + Sources class (§2.2).
- `embeddings.md` — normative for the Embeddings class (§2.3).
- `shapes.md` — normative for the Shapes class (§2.4).
- `trust.md` — normative for the Signed class (§2.5).
