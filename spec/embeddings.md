# CCX 3.0 — Embeddings

This document specifies the **Embeddings** conformance class (Class 3) of the
CCX 3.0 format. It defines the meaning of embedding descriptors in the manifest,
the three levels at which a package may declare embeddings, the constraints on
vector sidecar files, and the obligations of readers and writers.

> Implementation status: ENFORCED — the reference reader grants the `embeddings`
> class via `validate()`; writer support via `PackageBuilder.add_embeddings`;
> vector-sidecar reading via the optional `embeddings` extra (pyarrow).

Normative keywords ("MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL") are to be
interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when,
they appear in all capitals, as shown here. Text not written with these keywords
is explanatory and non-normative.

Cross-references are to sibling files in `spec/`. The conformance fixture map is
in `conformance.md` §4.3.

---

## 1. Scope and relationship to Core

Embeddings are **OPTIONAL** and are never part of the Core conformance class. A
package that does not carry embeddings conforms to Core alone; it need not
include any embedding-related fields in its manifest.

The Embeddings class is layered on Core: a package that conforms to the
Embeddings class MUST also satisfy every normative requirement of Core
(`ccx-3.0.md`). Higher classes (Shapes, Signed) may in turn layer on the
Embeddings class, but they MUST NOT depend on any specific embedding being
present.

An implementation that does not support the Embeddings class MUST ignore
embedding descriptors and any sidecar assets they reference. This follows
directly from the reader contract in `ccx-3.0.md` §5: unrecognized extension
material MUST be silently ignored rather than causing a failure.

---

## 2. Declaration levels

A package declares embeddings at exactly one of three levels. The level is
determined by inspecting the manifest `embeddings` array (defined in
`manifest.md` §8).

### 2.1 Absent

The manifest carries no `embeddings` field, or the `embeddings` array is empty.

This is the smallest, most portable case. No embedding metadata and no vector
data are present. Producers who have not computed embeddings, or who choose not
to distribute them, MUST use this level.

A reader MUST treat the absence of the `embeddings` field as equivalent to an
empty array and MUST NOT treat it as an error.

### 2.2 Provenance-only

The manifest contains one or more embedding descriptors, each with
`"included": false`.

At this level the manifest records the **provenance** of a set of vectors —
model, provider, dimensionality, and coverage — without shipping the vector data
itself. No sidecar asset is included in the package. A consumer that wishes to
use embeddings can use the descriptor to recompute compatible vectors from
scratch, or to verify that locally cached vectors were produced under the same
conditions.

A provenance-only descriptor MUST NOT reference a sidecar `path`. A reader that
encounters a descriptor with `"included": false` and a non-null `path` MUST
treat the package as invalid.

### 2.3 Included

The manifest contains one or more embedding descriptors, each with
`"included": true`, and each descriptor references a binary sidecar asset that
is present in the package.

At this level both the embedding provenance and the embedding vectors are
distributed together. Section 3 defines the sidecar requirements.

---

## 3. Included vector sidecars

### 3.1 Binary format requirement

Vectors MUST NOT be serialized as JSON text. Floating-point vector data
serialized as JSON text is wasteful and slow: a single 64-bit float requires up
to 22 bytes as a JSON number versus 8 bytes in a native binary encoding.

Each sidecar MUST be a **content-addressed binary file** registered in the
manifest `assets` array (see `manifest.md` §7). The file MUST use a binary
format designed for columnar or record-oriented floating-point data. Apache
Parquet is the RECOMMENDED format; other formats MAY be used provided they are
declared via the descriptor's `format` field and are documented by the producer.

### 3.2 Required sidecar structure

When using Apache Parquet (or any columnar format), the sidecar MUST contain at
minimum:

- An **`@id` column** whose values are the IRIs of the knowledge-graph nodes the
  vectors correspond to. Each value MUST be a string that matches the `@id` of a
  node in the package's default graph or a declared named graph.
- A **vector column** whose values are the embedding vectors for the
  corresponding nodes. Each vector MUST have exactly the number of dimensions
  declared in the descriptor's `dimensions` field.

The `@id` column provides the binding between the sidecar and the knowledge
graph; a sidecar without an `@id` column is not self-describing and is therefore
non-conformant.

### 3.3 Content-addressing and checksum

A sidecar asset MUST be declared in the manifest `assets` array with a `path`
that resolves to a ZIP entry present in the package. The `sha256` and `sha512`
fields MUST be present and MUST match the exact bytes of that entry, as required
by `manifest.md` §3.1 and §3.2.

A reader MUST verify both digests before using any sidecar content, and MUST
treat any checksum mismatch as a fatal validation error.

### 3.4 Provenance always travels with vectors

An included sidecar MUST have a corresponding descriptor so that the vectors are
never an inert, unidentified blob. A sidecar that is present in the `assets`
array but has no referencing embedding descriptor is not a conformant embedding
sidecar at the Embeddings class level; producers MUST NOT produce such packages,
and readers that detect this condition SHOULD surface a warning.

---

## 4. Embedding descriptors

### 4.1 Location in the manifest

Embedding descriptors are carried in the manifest's top-level `embeddings` array
(defined in `manifest.md` §8). Each element of that array is one embedding
descriptor object. The `embeddings` key MUST NOT appear at any level of the
manifest other than the top level.

### 4.2 Provenance fields

Every descriptor MUST carry `model` (string) and `dimensions` (positive
integer). It SHOULD carry `provider` (string) — `provider` together with
`model` identifies a reproducible model version, so Chaos Cypher producers
SHOULD emit it whenever known. It MAY carry `coverage` (string or object;
describes which nodes are embedded) and `included` (boolean; `true` when a
sidecar ships, default `false` = provenance-only). This matches the manifest
schema, which requires `model` + `dimensions` (`manifest.md` §1: prose and
schema MUST agree).

| Field | Type | Obligation | Meaning |
|-------|------|------------|---------|
| `model` | string | REQUIRED | The identifier of the embedding model used to compute the vectors (for example `"text-embedding-3-small"` or a resolvable model card IRI). |
| `dimensions` | integer | REQUIRED | The number of floating-point dimensions in each vector. MUST be a positive integer. A reader MUST reject a descriptor whose `dimensions` value does not match the actual column width found in the sidecar. |
| `provider` | string | RECOMMENDED | The organization or system that hosts or publishes the model (for example `"openai"` or `"huggingface"`). Together with `model`, identifies a reproducible model version. |
| `coverage` | string or object | OPTIONAL | A human-readable or structured description of which nodes in the package have been embedded. RECOMMENDED values are `"all"` (every node in the default graph), a named-graph reference, or a structured filter object. |
| `included` | boolean | OPTIONAL | `true` if a vector sidecar is included in this package; `false` (default) if the descriptor is provenance-only (Section 2.2–2.3). |

### 4.3 Additional fields for included descriptors

When `included` is `true`, the descriptor MUST also carry:

| Field | Type | Meaning |
|-------|------|---------|
| `path` | string | The `path` value of the corresponding `assets[]` entry. MUST be a non-empty string that matches exactly the `path` declared for the sidecar in the manifest `assets` array. |
| `format` | string | The binary format of the sidecar. SHOULD be `"parquet"` (Apache Parquet). The formats `"safetensors"`, `"lance"`, and `"npy"` MAY be used; any other value MAY be used provided the producer documents it out-of-band. The CCX format is intentionally open to the evolving ecosystem of binary tensor formats. |

A reader MUST resolve the `path` against the manifest `assets` array, verify
that the referenced entry exists in the ZIP, and verify its checksums before
loading any vector data.

Multiple descriptors MAY be present — for example, one chunk-level set and one
entity-level set — each referencing its own distinct sidecar (see Section 4.4).

### 4.4 Multiple embedding sets

A package MAY carry more than one embedding set by including multiple descriptor
entries in the `embeddings` array — for example, vectors computed by two
different models, or vectors at different dimensionalities for the same model.

Each descriptor entry MUST carry its own complete provenance (the REQUIRED and
RECOMMENDED fields in Section 4.2). When multiple included descriptors are
present, each MUST reference a distinct sidecar `path`; two descriptors MUST
NOT share a sidecar.

A reader MAY choose to load only a subset of the available embedding sets. It
MUST NOT treat the presence of additional sets as an error.

---

## 5. Reader obligations

### 5.1 Ignoring embeddings

A reader that does not implement the Embeddings class MUST ignore the `embeddings`
array and any sidecar assets it references. This is an instance of the general
extension-ignorance rule in `ccx-3.0.md` §5.

### 5.2 Validating descriptors

A reader that does implement the Embeddings class MUST:

1. Check that every descriptor in the `embeddings` array contains the REQUIRED
   fields `model` and `dimensions` (Section 4.2).
2. For each included descriptor (`"included": true`), verify that the referenced
   `path` names an entry in the manifest `assets` array.
3. Verify the `sha256` and `sha512` checksums of every referenced sidecar before
   consuming its content.
4. Reject the package if the `dimensions` declared in a descriptor does not
   match the actual vector width in the sidecar.
5. Reject the package if a descriptor with `"included": false` carries a
   non-null `path` (Section 2.2).

### 5.3 Error handling

A checksum mismatch on a sidecar MUST be treated as a fatal validation error,
consistent with `manifest.md` §3.2. A descriptor that is missing required
provenance fields MUST be treated as invalid. All other malformed-descriptor
conditions (unrecognized `format`, unknown fields) SHOULD be surfaced as
warnings; unrecognized fields MUST be ignored per the `additionalProperties`
policy of `manifest.md` §1.

---

## 6. Writer obligations

A writer producing an Embeddings-class package MUST:

1. Include at least one embedding descriptor in the manifest `embeddings` array.
2. Ensure every descriptor contains the REQUIRED fields `model` and `dimensions`,
   and SHOULD include `provider` (Section 4.2).
3. For each included descriptor, register the sidecar in the manifest `assets`
   array with correct `sha256` and `sha512` digests computed over the actual
   sidecar bytes.
4. Serialize vector data in a binary format (Section 3.1); a writer MUST NOT
   emit vectors as JSON text.
5. Ensure the sidecar contains an `@id` column whose values match IRIs present
   in the package's graphs (Section 3.2).
6. Ensure the number of dimensions in the sidecar matches the `dimensions` field
   declared in the descriptor (Section 4.2).

---

## 7. Worked example (informative)

The following manifest fragment shows a package carrying two embedding sets: one
provenance-only descriptor for a high-dimensional model, and one included
descriptor backed by a Parquet sidecar. This example is informative; the
normative rules are those in Sections 2–6 above.

```json
{
  "ccx_version": "3.0",
  "name": "demo/people",
  "package_version": "1.2.0",
  "graphs": [ { "…": "…" } ],
  "assets": [
    {
      "path": "assets/embeddings-small.parquet",
      "media_type": "application/vnd.apache.parquet",
      "sha256": "…",
      "sha512": "…"
    }
  ],
  "embeddings": [
    {
      "model": "text-embedding-3-large",
      "provider": "openai",
      "dimensions": 3072,
      "coverage": "all",
      "included": false
    },
    {
      "model": "text-embedding-3-small",
      "provider": "openai",
      "dimensions": 1536,
      "coverage": "all",
      "included": true,
      "path": "assets/embeddings-small.parquet",
      "format": "parquet"
    }
  ]
}
```

In this example:
- The first descriptor records that `text-embedding-3-large` vectors were used
  during the package's authoring process but are not included; a consumer wishing
  to use 3072-dimensional vectors must recompute them.
- The second descriptor ships 1536-dimensional vectors in
  `assets/embeddings-small.parquet`. The sidecar is registered in `assets` with
  checksums; a reader MUST verify those checksums before loading the file.
- The `@id` column in `embeddings-small.parquet` maps each row to a node IRI in
  the package's knowledge graph.

---

## 8. Cross-references

- `ccx-3.0.md` — Core container model, reader security contract, and the
  extension-ignorance rule (§5) that governs readers not implementing this class.
- `manifest.md` — normative definition of the `embeddings` descriptor shape
  (§8), the `assets` registry (§7), the existence and checksum constraints
  (§3.1–3.2), and the `additionalProperties` policy (§1).
- `conformance.md` — normative Embeddings class membership rules (§2.3) and the
  fixture map for this class (§4.3).
- `knowledge.md` — the default graph and node IRI conventions that the sidecar
  `@id` column MUST reference.
