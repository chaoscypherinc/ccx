# CCX Vocabulary (`ccx:`)

The normative `ccx:` vocabulary. All terms are minted under the base IRI
`https://w3id.org/ccx/` and are referred to with the prefix `ccx:` (so
`ccx:Relationship` expands to `https://w3id.org/ccx/Relationship`).

Normative keywords (MUST, SHOULD, MAY) follow RFC 2119 / RFC 8174.

## The bundled context is the term→IRI map

**`src/ccx/schemas/context.jsonld` (the bundled `@context`) is the machine
term→IRI map and MUST define every term enumerated in this document.** A term is
not part of the CCX vocabulary unless it appears in both this normative document
and the bundled context with the same expansion. Consumers resolve compact terms
in `knowledge` graphs against the bundled context, so the two MUST agree.

Higher-conformance-class terms — the sources/citation terms (Core + Sources) and
the embedding terms (Embeddings) — are listed in their own sections below. Each is
also present in the bundled context. A term is part of the CCX vocabulary only when
it appears in both this document and the bundled context with the same expansion.

> Implementation status: Core edge terms present in the bundled context; higher-class terms added by their modules.

## Core edge terms

CCX models an edge as a node ("edge-as-node"): a relationship is reified into a
`ccx:Relationship` resource so that properties, provenance, and citations can
attach to the relationship itself rather than only to its endpoints. The three
edge properties (`ccx:subject`, `ccx:predicate`, `ccx:object`) carry the reified
triple.

### Classes

| IRI | `rdfs:label` | Definition |
|-----|--------------|------------|
| `https://w3id.org/ccx/Relationship` | Relationship | An "edge-as-node" resource that reifies a relationship between two resources so that properties and citations can attach to the relationship itself. Instances carry exactly one `ccx:subject`, one `ccx:predicate`, and one `ccx:object`. |

### Properties

| IRI | `rdfs:label` | Definition | Domain | Range |
|-----|--------------|------------|--------|-------|
| `https://w3id.org/ccx/subject` | subject | The subject resource of a `ccx:Relationship` — the resource the edge points *from*. | `ccx:Relationship` | resource (IRI node) |
| `https://w3id.org/ccx/predicate` | predicate | The predicate of a `ccx:Relationship` — the relationship type, identifying what the edge asserts between subject and object. | `ccx:Relationship` | IRI (property/term) |
| `https://w3id.org/ccx/object` | object | The object resource of a `ccx:Relationship` — the resource the edge points *to*. | `ccx:Relationship` | resource (IRI node) |

#### `ccx:Relationship`

- **IRI:** `https://w3id.org/ccx/Relationship`
- **`rdfs:label`:** Relationship
- **Definition:** An "edge-as-node" resource. A `ccx:Relationship` reifies a
  relationship so that additional properties (and, in higher conformance classes,
  source citations) can be attached to the edge itself. Each instance MUST have
  exactly one `ccx:subject`, one `ccx:predicate`, and one `ccx:object`.

#### `ccx:subject`

- **IRI:** `https://w3id.org/ccx/subject`
- **`rdfs:label`:** subject
- **Definition:** The subject resource of a `ccx:Relationship` (the resource the
  edge points *from*).
- **Domain:** `ccx:Relationship`
- **Range:** a resource (IRI node).

#### `ccx:predicate`

- **IRI:** `https://w3id.org/ccx/predicate`
- **`rdfs:label`:** predicate
- **Definition:** The predicate (relationship type) of a `ccx:Relationship`,
  identifying what is asserted between the subject and the object.
- **Domain:** `ccx:Relationship`
- **Range:** an IRI denoting a property or relationship term.

#### `ccx:object`

- **IRI:** `https://w3id.org/ccx/object`
- **`rdfs:label`:** object
- **Definition:** The object resource of a `ccx:Relationship` (the resource the
  edge points *to*).
- **Domain:** `ccx:Relationship`
- **Range:** a resource (IRI node).

## Sources and citation terms (Core + Sources)

These terms describe sources, their chunks, and citation anchors. They are
normative for the **Core + Sources** conformance class (see `sources.md`).

### Classes

| IRI | `rdfs:label` | Definition |
|-----|--------------|------------|
| `https://w3id.org/ccx/Source` | Source | A source document backing the package's assertions; its metadata, provenance, and media mode are recorded in `sources.jsonl` and the manifest. |
| `https://w3id.org/ccx/Chunk` | Chunk | A contiguous span of a source's extracted text, identified by an offset selector rather than a copy of the text. |
| `https://w3id.org/ccx/Citation` | Citation | A link from an assertion (a node or a `ccx:Relationship`) to the source evidence that supports it, anchored by a `ccx:selector`. |

### Properties

| IRI | `rdfs:label` | Definition | Domain | Range |
|-----|--------------|------------|--------|-------|
| `https://w3id.org/ccx/selector` | selector | A W3C Web Annotation / Media Fragments selector identifying the anchored region of a source (text offset, page region, timecode range, image region). | `ccx:Citation` / `ccx:Chunk` | a Web Annotation selector |
| `https://w3id.org/ccx/sourceMode` | sourceMode | The media mode of a source — `embedded`, `referenced`, or `derived-only`; mirrors the manifest asset entry's `source_mode`. | `ccx:Source` | string (one of the three modes) |
| `https://w3id.org/ccx/extractedBy` | extractedBy | The extraction provenance of a source's derived text — the parser, OCR, or transcription tool name and version. | `ccx:Source` | string / structured provenance |

#### `ccx:citation`

- **IRI:** `https://w3id.org/ccx/citation`
- **`rdfs:label`:** citation
- **Definition:** Links a claim (a `ccx:Relationship` or a node) to the source evidence supporting it.
- **Domain:** a claim resource.
- **Range:** a `ccx:Citation` / `ccx:Chunk` / `ccx:Source`.

A CCX citation is modeled on the **W3C Web Annotation** model (`oa:Annotation`: the cited region is the annotation target); `ccx:citation` is the link, and the two fields below are the only CCX-specific additions, used because `oa:` has no standard equivalent.

#### `ccx:confidence`

- **IRI:** `https://w3id.org/ccx/confidence`
- **`rdfs:label`:** confidence
- **Definition:** A 0.0–1.0 score for an extracted citation or relationship.

#### `ccx:extractionMethod`

- **IRI:** `https://w3id.org/ccx/extractionMethod`
- **`rdfs:label`:** extractionMethod
- **Definition:** The method or tool that produced a citation (e.g. `"llm/gpt-4o"`, `"regex"`).

## Embedding terms (Embeddings)

Normative for the **Embeddings** conformance class (see `embeddings.md`). The
embedding *descriptor* itself lives in the manifest (`manifest.md`); these terms
let an entity or chunk reference embedding provenance from RDF.

| IRI | `rdfs:label` | Definition | Domain | Range |
|-----|--------------|------------|--------|-------|
| `https://w3id.org/ccx/embeddingModel` | embeddingModel | The model that produced an embedding (name; by convention also provider and version). | a vector-bearing resource | string |
| `https://w3id.org/ccx/dimensions` | dimensions | The dimensionality of an embedding vector. | a vector-bearing resource | integer |
