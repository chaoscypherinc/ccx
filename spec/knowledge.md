# CCX 3.0 — The Knowledge Graph

This module specifies `knowledge.jsonld`: the JSON-LD document that carries a
CCX package's primary knowledge graph. It is part of the **Core** conformance
class. The container, the manifest, and the package-wide security rules are
specified in [`ccx-3.0.md`](./ccx-3.0.md); the `ccx:` terms referenced here are
defined in [`vocabulary.md`](./vocabulary.md).

Normative keywords (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**)
are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when,
they appear in all capitals.

> Implementation status: Core — the reference reader loads knowledge.jsonld into the rdflib default graph; remote-context rejection is enforced.

## 1. Role in the RDF Dataset

A `.ccx` package is, semantically, an **RDF Dataset**. The `knowledge` graph —
the manifest graph entry whose `role` is `default` (equivalently, whose
`namespace` is `ccx`) — is the **default graph** of that dataset. Every other
declared graph is a named graph (see [`ccx-3.0.md`](./ccx-3.0.md) for the
container model and [`manifest.md`](./manifest.md) for the graph registry).

1.1. A Core package **MUST** contain exactly one default graph, serialized as a
single JSON-LD document. Its conventional path is `knowledge.jsonld`; the
authoritative path, media type, and checksums are taken from the manifest graph
entry, not from the filename.

1.2. The media type of `knowledge.jsonld` **MUST** be `application/ld+json`.

1.3. A reader **MUST** load `knowledge.jsonld` as the default graph of the
package's RDF Dataset. Triples in `knowledge.jsonld` that carry no graph name
become default-graph triples; readers **MUST NOT** silently relocate them into a
named graph.

## 2. JSON-LD requirements

2.1. `knowledge.jsonld` **MUST** be a single, well-formed JSON document that is
valid JSON-LD 1.1 and that expands without error against the package's bundled
`@context` (see §3).

2.2. The document **MUST** be shaped as one of:

- a top-level **node object** (a JSON object describing a single resource), or
- a JSON object containing a top-level **`@graph` array** of node objects.

A bare top-level JSON array (a list of node objects without an enclosing object)
**SHOULD NOT** be used, because it leaves no place to attach the document-level
`@context`; producers **MUST** instead wrap such a list in an object with
`@context` and `@graph`.

2.3. Every node object that denotes a named (non-blank) resource **MUST** carry
an `@id`. Authors **SHOULD** assign an `@id` to every resource that another
package, graph, or citation might reference, so that the resource can be the
target of a cross-package merge or a `ccx:derived_from` link (see §4 and §5.4).
Blank nodes **MAY** be used for purely structural, locally-scoped values.

2.4. Each node object **SHOULD** declare a `@type` (one or more), using a term
defined in the bundled context. Untyped nodes are permitted but **SHOULD** be
avoided for top-level entities.

2.5. The empty graph (a document with an empty `@graph` array) is valid and
denotes a package that asserts no default-graph triples.

## 3. The `@context`

3.1. `knowledge.jsonld` **MUST** resolve its terms against the package's bundled
context. A producer **MUST** do one of the following:

- reference the bundled `context.jsonld` by its **package-relative** path or by
  a `urn:`/relative reference that the reader resolves to the bundled file; or
- inline, as the value of `@context`, a context object equivalent to the bundled
  `context.jsonld`.

3.2. A reader **MUST reject** the package (treat it as invalid and refuse to load
the graph) if `knowledge.jsonld` references any **remote** `@context` — that is,
any `@context` value that is an `http://` or `https://` IRI, whether it appears
as a bare string or as a string entry inside a `@context` array. This rule
applies to node-scoped contexts nested anywhere in the document, not only at the
top level.

3.3. A reader **MUST reject** the package if `knowledge.jsonld` uses JSON-LD
1.1 `@import` to pull in a remote context.

3.4. These prohibitions are security requirements: read-time context resolution
**MUST NOT** trigger any network access. The package is self-contained, and its
checksums cover the bundled context, so a reader can verify exactly which terms
are in force. See [`ccx-3.0.md`](./ccx-3.0.md) §6 (Security) for the normative
statement of the no-network reader contract that this rule implements.

3.5. A relative or in-package `@context` reference that, after resolution, would
require fetching a resource not present in the package **MUST** be treated the
same as a remote context and rejected.

## 4. IRIs and identity

4.1. **Vocabulary.** CCX-defined terms live in the vocabulary namespace
`https://w3id.org/ccx/`, bound to the prefix `ccx:` by the bundled context (so,
for example, `ccx:Relationship` denotes `https://w3id.org/ccx/Relationship`).
The vocabulary itself is specified in [`vocabulary.md`](./vocabulary.md).

4.2. **Entity identifiers.** Relative `@id` values for the package's own
entities resolve against the manifest's `base_iri`, which a reader **MUST** apply
as the JSON-LD `@base` for `knowledge.jsonld`. A producer **MUST** ensure that
the effective base used when authoring matches the manifest `base_iri`, so that
the IRIs a reader materializes are exactly those the producer intended.

4.3. **Choosing a base.** Authors **SHOULD** use a stable, dereferenceable-in-
principle base that they control — their own domain
(e.g. `https://example.org/kb/`) or a `https://w3id.org/ccx/...` path. A package
that has no web home **MAY** use a UUID-based URN base of the form
`urn:ccx:<uuid>` (for example, `urn:ccx:6f1c…:`). Authors **SHOULD NOT** invent
a base under a namespace they do not control.

4.4. **Identity is global and stable.** The same `@id` **MUST** denote the same
real-world entity across every package and graph in which it appears. Two
producers that mint different IRIs for the same entity are describing, as far as
CCX is concerned, two different entities; conversely, reusing an IRI is an
assertion that it is the *same* entity. This shared-identity guarantee is what
makes two values meaningful:

- **Cross-package merge** — loading two packages into one dataset correctly
  unifies a resource exactly when both use the same `@id` for it.
- **`ccx:derived_from`** — a provenance link from a resource to the resource it
  was derived from is only sound if both endpoints are denoted by stable IRIs.

4.5. A producer **MUST NOT** reassign an existing `@id` to a different entity in
a later package version. Identifier reuse for a different referent breaks every
downstream merge and provenance link. See [`versioning.md`](./versioning.md) for
the compatibility rule.

## 5. Modeling relationships (edges)

CCX expresses graph edges as RDF triples. Two modeling styles are normative,
chosen by whether the edge itself needs to carry properties or citations.

### 5.1. Plain triples (preferred for simple edges)

5.1.1. A simple, property-free relationship **SHOULD** be expressed as a plain
RDF triple: a single predicate linking subject to object directly
(for example, `:alice ccx:worksFor :acme`). This is the default and most
interoperable form, and it **SHOULD** be used whenever the edge needs no
attributes of its own.

### 5.2. Edge-as-node (required for property- or citation-bearing edges)

5.2.1. A relationship that must itself carry properties (such as a weight, a
confidence, a validity interval, or a qualifier) or that must carry one or more
citations **MUST** be modeled as **edge-as-node**: a distinct
`ccx:Relationship` resource that links the participants and to which the extra
properties and citations are attached.

5.2.2. A `ccx:Relationship` resource **MUST** identify the edge's subject,
predicate, and object using the corresponding `ccx:` terms defined in
[`vocabulary.md`](./vocabulary.md) (`ccx:subject`, `ccx:predicate`,
`ccx:object`). Additional properties and citation links **MUST** be attached to
the `ccx:Relationship` resource itself, not to the subject or object.

5.2.3. The `ccx:Relationship` resource **SHOULD** carry a stable `@id` (see §4),
so that the edge can itself be cited, merged, or referenced from another graph.

### 5.3. Reification and RDF-star

5.3.1. A producer **MUST NOT** be required to use RDF-star (quoted/embedded
triples) at this version of the format. The edge-as-node pattern is the
portable, mandated mechanism for attributing statements about a relationship,
and a Core-conformant reader is not required to understand RDF-star syntax.

5.3.2. Standard RDF reification (the `rdf:Statement` / `rdf:subject` /
`rdf:predicate` / `rdf:object` vocabulary) **SHOULD NOT** be used to attach
properties or citations to an edge; use `ccx:Relationship` (§5.2) instead, so
that all CCX edges-with-attributes share one shape.

### 5.4. Citations and provenance

5.4.1. Where an edge or a node is backed by a source, the citation **SHOULD** be
attached to the resource it qualifies (the `ccx:Relationship` for an edge, or
the node for a node-level claim). The citation vocabulary and the source-anchor
mechanism are specified in [`sources.md`](./sources.md); provenance links such
as `ccx:derived_from` are specified in [`vocabulary.md`](./vocabulary.md).

## 6. Example

The following `knowledge.jsonld` describes two entities joined by a plain-triple
edge (`worksFor`) and by a property- and citation-bearing edge modeled as a
`ccx:Relationship`. The document references the bundled context by its
package-relative path; `@id` values are relative and resolve against the
manifest `base_iri` (here `urn:ccx:demo:`).

```json
{
  "@context": "context.jsonld",
  "@graph": [
    {
      "@id": "alice",
      "@type": "Person",
      "name": "Alice Smith",
      "worksFor": { "@id": "acme" }
    },
    {
      "@id": "acme",
      "@type": "Organization",
      "name": "Acme Corporation"
    },
    {
      "@id": "rel/alice-worksfor-acme",
      "@type": "ccx:Relationship",
      "ccx:subject": { "@id": "alice" },
      "ccx:predicate": { "@id": "worksFor" },
      "ccx:object": { "@id": "acme" },
      "ccx:confidence": 0.92,
      "ccx:citation": { "@id": "ccx:source/hr-records#chunk-1" }
    }
  ]
}
```

In this example:

- `alice worksFor acme` is a **plain triple** — a direct edge with no attributes
  of its own.
- `rel/alice-worksfor-acme` is an **edge-as-node** `ccx:Relationship`: the
  confidence score and citation are attached to the relationship resource, not
  to `alice` or `acme`. Because the relationship has its own `@id`, the edge can
  be cited or merged like any other resource.

> The bundled `context.jsonld` binds the prefixes and compact terms used above;
> `ccx:confidence` and `ccx:citation` are defined in
> [`vocabulary.md`](./vocabulary.md).
