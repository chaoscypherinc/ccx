# CCX 3.0 — The Manifest

This document specifies `manifest.json`, the single mandatory metadata entry of
a CCX package. It defines the **semantics** of every manifest field and the
**constraints that JSON Schema cannot express**.

> Normative keywords ("MUST", "MUST NOT", "SHOULD", "MAY", etc.) are to be
> interpreted as described in RFC 2119 / RFC 8174 (see `ccx-3.0.md` §Conventions).

> Implementation status: Core fields enforced by manifest.schema.json + the
> reference reader. The Sources and Embeddings fields (`source_mode`, embedding
> descriptors) are now read and validated by the reference reader; the signing and
> per-source/graph licensing fields remain spec + fixture only.

## 1. Authority and the schema relationship

The JSON Schema `manifest.schema.json`
(`$id: https://w3id.org/ccx/schema/3.0/manifest.schema.json`) **is the
authoritative definition of manifest STRUCTURE**: the set of permitted fields,
their JSON types, required-vs-optional status, and value enumerations. A
manifest MUST validate against that schema.

This document defines manifest **SEMANTICS** — the meaning of each field — and
the additional constraints that JSON Schema cannot express (Section 3). Where
this prose and `manifest.schema.json` describe the same thing, the two MUST
agree. If a reader detects a divergence between them, that divergence is a
defect to be reported and corrected; neither artifact silently overrides the
other on matters of structure. On matters of meaning and cross-entry
constraints, this document governs.

The schema sets `additionalProperties: true` at both the manifest level and
within `graphs[]` and `assets[]` entries. This is deliberate: it permits the
higher-conformance-class fields specified in Section 4 (and in the class
modules) to appear without a schema revision. Producers MUST NOT use unknown
properties to contradict the semantics defined here, and consumers MUST ignore
properties they do not understand rather than rejecting the package.

## 2. Location and encoding

A conforming CCX package MUST contain exactly one ZIP entry named
`manifest.json` at the package root. It MUST be a UTF-8-encoded JSON object that
validates against `manifest.schema.json`. The container rules (entry order, the
`mimetype` entry, path normalization, and reader hardening) are defined in
`ccx-3.0.md`; this document assumes a manifest that has already been parsed and
schema-validated.

## 3. Constraints JSON Schema cannot express (normative)

The following constraints are normative and are **not** expressible in
`manifest.schema.json`. A conforming reader MUST enforce all of them, and a
conforming writer MUST satisfy all of them. A package that violates any of these
constraints is invalid even if it satisfies the JSON Schema.

### 3.1 Declared entries MUST exist

Every value of `graphs[].path` and every value of `assets[].path` MUST resolve
to an entry that exists in the package ZIP. A `path` that names a non-existent
ZIP entry makes the package invalid.

### 3.2 Declared checksums MUST match the bytes

For every `graphs[]` and `assets[]` entry, the declared `sha256` MUST equal the
SHA-256 digest, and the declared `sha512` MUST equal the SHA-512 digest, of the
exact bytes of the corresponding ZIP entry. A reader MUST verify both digests
and MUST treat any mismatch as a fatal validation error. (The digest encoding
is defined in `ccx-3.0.md`; it is the same for both algorithms.)

### 3.3 Exactly one default graph

The manifest MUST declare **exactly one** default graph — the `ccx`/`knowledge`
graph (Section 3.4). It SHOULD be marked `role: "default"`, and the reference
writer always emits this; however, a reader MUST treat the `ccx`/`knowledge` graph
as the default graph whether or not `role: "default"` is present — the
`namespace`/`name` pair is the authoritative identifier (see `ccx-3.0.md` §4.4).
No graph entry other than `ccx`/`knowledge` may carry `role: "default"`. The
`ccx`/`knowledge` default graph MAY be empty (i.e. its `@graph` array is `[]`);
this is the case for a sources-only package, where the first-class payload is
`sources.jsonl` rather than the knowledge graph (`ccx-3.0.md` §3.3).

### 3.4 The default graph MUST be the `ccx`/`knowledge` graph

The default graph entry MUST have `namespace: "ccx"` and `name: "knowledge"`, and
the `ccx`/`knowledge` graph MUST NOT be declared as a non-default named graph. The
semantics of the knowledge graph are defined in `knowledge.md`. The graph MAY be
empty (its `@graph` is `[]`) for a sources-only package (Section 3.3).

## 4. Conformance classes for fields

Manifest fields fall into two tiers.

**Core-required fields** MUST be present in every conforming CCX package. They
are enforced by both `manifest.schema.json` and the reference reader:

- top-level: `ccx_version`, `name`, `package_version`, `graphs`;
- within every `graphs[]` entry: `namespace`, `name`, `path`, `media_type`,
  `sha256`, `sha512`.

**Higher-class fields** are OPTIONAL at Core and are introduced (or made
meaningful) by higher conformance classes. They are specified here and in the
class modules, are accommodated by the schema (via `additionalProperties`), and
are exercised by conformance fixtures, but carry no reference-library behavior
yet:

- per-source and per-graph `license` overrides (Section 5.4);
- the asset `source_mode` field (Section 7);
- embedding descriptor(s) (Section 8);
- signature reference(s) (Section 9).

All other top-level descriptive, identity, and provenance fields named in
Section 5 are OPTIONAL but belong to the Core vocabulary.

See `conformance.md` for the normative definition of each conformance class.

## 5. Top-level field reference

### 5.1 Format version

- **`ccx_version`** (string, **Core-required**) — the CCX format version this
  package targets, e.g. `"3.0"`. Compatibility rules are defined in
  `versioning.md`. A reader MUST refuse a package whose `ccx_version` it does
  not support.

### 5.2 Identity

- **`name`** (string, **Core-required**) — the package identifier. SHOULD be a
  stable, namespaced slug (for example `"demo/people"`). It identifies the
  package across versions.
- **`package_version`** (string, **Core-required**) — the version of *this
  package's content*, distinct from `ccx_version`. Producers SHOULD use
  Semantic Versioning. See `versioning.md`.

### 5.3 Descriptive

These fields are OPTIONAL and carry no semantic constraints beyond their JSON
type; they are for human and catalog consumption.

- **`title`** (string) — a human-readable title.
- **`description`** (string) — a longer human-readable description.
- **`tags`** (array of strings) — free-form classification labels. A reader MUST
  ignore tags it does not understand.
- **`author`** (string) — the responsible person or organization.
- **`created_at`** (string) — the package creation timestamp. SHOULD be an
  RFC 3339 / ISO 8601 date-time in UTC.

### 5.4 Licensing

- **`license`** (string, OPTIONAL but RECOMMENDED) — the license governing the
  package as a whole. Its value MUST be a valid SPDX license identifier (for
  example `"CC-BY-4.0"` or `"Apache-2.0"`). This is the default license for all
  contained graphs, assets, and sources unless overridden.
- **Per-graph and per-source `license` overrides** (higher-class) — an
  individual `graphs[]` entry, `assets[]` entry, or source record MAY carry its
  own `license` (an SPDX identifier) that overrides the package-level `license`
  for that entry only. Per-source licensing is detailed in `sources.md`. Where
  no override is present, the package-level `license` applies.

### 5.5 Provenance

These fields are OPTIONAL and describe where the package came from and what it
depends on.

- **`derived_from`** — an object mapping each upstream package this package was
  derived from to the `package_version` it was derived from (a `name` →
  `version` map).
- **`dependencies`** — an object mapping each package this package depends on to
  a required version or version range (a `name` → `version` map).

### 5.6 Base IRI

- **`base_iri`** (string, OPTIONAL) — the base IRI against which relative IRIs in
  the package's graphs are resolved. When present it SHOULD be an absolute IRI
  (an `http(s):` or `urn:` IRI is typical, e.g. `"urn:ccx:demo:"`). Its
  interaction with the JSON-LD context and relative-IRI resolution is defined in
  `knowledge.md`.

### 5.7 Generator

- **`generator`** (string, OPTIONAL) — a free-form identifier of the tool and
  version that produced the package (for example `"ccx-format/3.0.1"`). It is
  informational only; a reader MUST NOT make trust or validity decisions based
  on `generator`.

## 6. The graph registry — `graphs`

**`graphs`** (array, **Core-required**, MUST contain at least one entry) is the
registry of every RDF named graph in the package. Each element is an object with
these fields:

| Field | Tier | Type | Meaning |
|-------|------|------|---------|
| `namespace` | **Core-required** | string | The graph's namespace prefix. The default graph MUST use `"ccx"`. |
| `name` | **Core-required** | string | The graph's local name within its namespace. The default graph MUST use `"knowledge"`. |
| `role` | optional | string, enum `["default"]` | SHOULD be present and equal to `"default"` on the `ccx`/`knowledge` default graph (Section 3.3–3.4); absent on all named graphs. |
| `path` | **Core-required** | string | The ZIP entry holding the graph's serialization. MUST exist (Section 3.1). |
| `media_type` | **Core-required** | string | The IANA media type of the serialization, e.g. `"application/ld+json"`. |
| `sha256` | **Core-required** | string | SHA-256 of the entry's bytes. MUST match (Section 3.2). |
| `sha512` | **Core-required** | string | SHA-512 of the entry's bytes. MUST match (Section 3.2). |
| `license` | higher-class | string | OPTIONAL SPDX identifier overriding the package `license` for this graph (Section 5.4). |

The `(namespace, name)` pair identifies the graph and SHOULD be unique within
the manifest. The `ccx`/`knowledge` graph is the sole default graph; all other
entries are named graphs (the format's one extension mechanism), as described in
`ccx-3.0.md`.

## 7. The asset registry — `assets`

**`assets`** (array, OPTIONAL) is the registry of non-graph binary or text
payloads carried by the package (for example cited source documents or embedding
sidecars). When omitted it is treated as empty. Each element is an object with
these fields:

| Field | Tier | Type | Meaning |
|-------|------|------|---------|
| `path` | **Core-required** (within an asset) | string | The ZIP entry holding the asset bytes. MUST exist (Section 3.1). |
| `media_type` | **Core-required** (within an asset) | string | The IANA media type of the asset bytes. |
| `sha256` | **Core-required** (within an asset) | string | SHA-256 of the entry's bytes. MUST match (Section 3.2). |
| `sha512` | **Core-required** (within an asset) | string | SHA-512 of the entry's bytes. MUST match (Section 3.2). |
| `source_mode` | higher-class | string, one of `embedded`, `referenced`, `derived-only` | OPTIONAL. How the source material relates to this asset (see below). |
| `license` | higher-class | string | OPTIONAL SPDX identifier overriding the package `license` for this asset (Section 5.4). |

"Within an asset, Core-required" means: if an `assets[]` entry is present, these
four fields MUST be present on it. The `assets` array itself is OPTIONAL at the
package level.

`source_mode` values (higher-class; full semantics in `sources.md`):

- **`embedded`** — the source material's bytes are carried in this asset entry
  inside the package.
- **`referenced`** — the asset records a reference to source material that is not
  carried in the package (only its identity and checksum metadata travel).
- **`derived-only`** — the package retains derived artifacts (e.g. extracted
  text or annotations) but not the original source bytes.

## 8. Embedding descriptors (higher-class)

A package in the Embeddings class declares its vector embeddings through one or
more embedding descriptors carried in the manifest. A descriptor identifies the
embedding model, the vector dimensionality, and the content-addressed vector
sidecar asset it corresponds to. The normative structure and field semantics of
embedding descriptors are defined in `embeddings.md`; their vector sidecars are
registered in `assets` (Section 7) and are subject to the existence and checksum
constraints of Section 3.

## 9. Signature references (higher-class)

A package in the Signed class carries one or more signature references in the
manifest, each pointing to a Sigstore-style signature over the manifest. The
normative structure, the signed payload, and the verification procedure are
defined in `trust.md`. A reader MUST NOT treat the presence of a signature
reference as proof of validity; signatures are verified per `trust.md`, and
checksum and existence constraints (Section 3) still apply.

## 10. Worked example (informative)

The following Core manifest declares the mandatory `ccx`/`knowledge` default
graph plus one application named graph and no assets. It is informative; the
normative rules are those above.

```json
{
  "ccx_version": "3.0",
  "name": "demo/people",
  "package_version": "1.0.0",
  "license": "CC-BY-4.0",
  "base_iri": "urn:ccx:demo:",
  "graphs": [
    {
      "namespace": "ccx",
      "role": "default",
      "name": "knowledge",
      "path": "knowledge.jsonld",
      "media_type": "application/ld+json",
      "sha256": "…",
      "sha512": "…"
    },
    {
      "namespace": "acme",
      "name": "notes",
      "path": "graphs/acme.notes.jsonld",
      "media_type": "application/ld+json",
      "sha256": "…",
      "sha512": "…"
    }
  ],
  "assets": []
}
```

## 11. Cross-references

- `ccx-3.0.md` — model, container, naming, reader contract, security, checksum
  encoding.
- `knowledge.md` — the `ccx`/`knowledge` default graph, IRIs, and `base_iri`
  resolution.
- `versioning.md` — `ccx_version` and `package_version` compatibility rules.
- `conformance.md` — normative conformance-class membership.
- `sources.md`, `embeddings.md`, `trust.md`, `shapes.md` — higher-class modules
  referenced above.
