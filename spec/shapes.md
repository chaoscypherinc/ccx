# CCX 3.0 — Shapes (Conformance Class 4)

This document is normative. It defines the **Shapes** conformance class for CCX
3.0 packages: the presence, structure, and interpretation of SHACL shapes carried
inside a package as `shapes.ttl`.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when,
they appear in all capitals, as shown here.

Text not written with these keywords is explanatory and non-normative.

Cross-references are to sibling files in `spec/`. The conformance-class hierarchy
is defined in `conformance.md` §2.

> Implementation status: ENFORCED — the reference reader grants the `shapes`
> class via `validate()` (rdflib); writer support via `PackageBuilder.add_shapes`;
> SHACL data-validation via the optional `shapes` extra (pyshacl).

---

## §1 Scope

The Shapes conformance class adds an OPTIONAL `shapes.ttl` entry to the CCX
package ZIP. When present, `shapes.ttl` is a [W3C SHACL](https://www.w3.org/TR/shacl/)
shapes graph expressed in Turtle syntax that describes or constrains the custom
(non-schema.org) vocabulary used by the package's knowledge graph.

This document specifies:

1. The conditions under which `shapes.ttl` MUST be declared and checksummed in
   the manifest (§2).
2. The single shapes language permitted in CCX and the constraints on its use (§3).
3. The reader contract for packages that carry or omit `shapes.ttl` (§4).
4. The syntactic validity requirement for `shapes.ttl` when present (§5).

---

## §2 Presence and Manifest Declaration

### 2.1 Optional inclusion

A package MAY include a file named `shapes.ttl` at the package root. The
inclusion of `shapes.ttl` is OPTIONAL at the Core conformance class; it becomes
normatively required only when a package claims Shapes-class conformance (see
`conformance.md` §2.4).

### 2.2 Manifest entry when present

When `shapes.ttl` is present in the package ZIP, it MUST be declared as an entry
in the manifest's `graphs` or `assets` registry in `manifest.json`. The manifest
entry for `shapes.ttl` MUST satisfy all of the following:

1. **Path.** The `path` field of the entry MUST be `"shapes.ttl"`.

2. **Media type.** The `media_type` field MUST be `"text/turtle"`.

3. **Checksums.** The entry MUST carry both a `sha256` field and a `sha512`
   field, each containing the corresponding digest of the exact bytes of the
   `shapes.ttl` ZIP entry, encoded as standard base64 per `trust.md` §2.2 (the
   same encoding used for every CCX checksum). A reader MUST verify both digests
   and MUST treat any mismatch as a fatal error (see `trust.md` §2 and
   `ccx-3.0.md` §5).

4. **Existence.** Because `shapes.ttl` is declared in the manifest, §3.1 of
   `manifest.md` applies: the declared path MUST resolve to a ZIP entry that
   exists in the package. A declared path that names an absent ZIP entry makes
   the package invalid.

A package that includes `shapes.ttl` but does not declare it in the manifest
does not conform to the Shapes class and does not carry Core guarantees for
the shapes data.

### 2.3 No manifest entry when absent

When `shapes.ttl` is not included in the package ZIP, the manifest MUST NOT
contain an entry whose `path` is `"shapes.ttl"`. A manifest entry that declares
a non-existent file violates `manifest.md` §3.1.

---

## §3 Shapes Language

### 3.1 SHACL is the single shapes language

CCX uses [W3C SHACL (Shapes Constraint Language)](https://www.w3.org/TR/shacl/)
as the single shapes language. A conformant `shapes.ttl` MUST be expressed
using SHACL vocabulary. No alternative or competing shapes language (for example,
ShEx) is defined by this specification; a producer that wishes to carry shapes in
a CCX package MUST use SHACL.

The SHACL shapes graph MUST be serialized in Turtle (`.ttl`). Other RDF
serializations of SHACL (for example, JSON-LD or N-Triples) are not accepted by
this specification; the entry name `shapes.ttl` and the media type `text/turtle`
are both normative identifiers of the required serialization.

### 3.2 Human-readable annotations

Within `shapes.ttl`, producers MAY use `rdfs:label` and `rdfs:comment` (from the
[RDF Schema vocabulary](https://www.w3.org/TR/rdf-schema/)) to attach
human-readable documentation to shapes, node shapes, property shapes, and
individual constraints. These annotations are informational and do not affect
shape evaluation. Readers MUST NOT treat the absence of `rdfs:label` or
`rdfs:comment` annotations as an error.

### 3.3 No OWL reasoner required

CCX does not mandate a Description Logic or OWL reasoner. `shapes.ttl` MUST NOT
be written in a way that requires OWL inference to be meaningful or correct. In
particular:

- Producers MUST NOT rely on OWL class entailments, property-chain axioms, or
  owl:sameAs merging as a prerequisite for SHACL evaluation to produce correct
  results.
- Producers MAY use OWL vocabulary (for example, `owl:Class` or
  `owl:ObjectProperty`) within `shapes.ttl` purely for annotation or
  documentation purposes, provided that the shapes themselves remain evaluable
  without a reasoner.

A reader that performs SHACL validation MUST be able to evaluate `shapes.ttl`
against the package's graphs without invoking an OWL reasoner. This ensures that
shapes-based validation is tractable and deterministic across all conformant
implementations.

### 3.4 Vocabulary coverage

The shapes in `shapes.ttl` SHOULD describe or constrain vocabulary terms and
node types that are specific to this package and are not already covered by the
core CCX vocabulary defined in `vocabulary.md`. Shapes that redundantly
re-describe standard schema.org or CCX core terms are permitted but carry no
additional normative weight.

---

## §4 Reader Contract

### 4.1 Absence is not an error

The ABSENCE of `shapes.ttl` from a package MUST NOT be treated as an error by a
reader. A reader that opens a Core-class package with no `shapes.ttl` entry MUST
load the package normally. Shapes are an optional extension; their absence does
not affect the integrity or usability of the package's knowledge graph (see
`ccx-3.0.md` §5 reader contract).

### 4.2 Validation is optional for readers

A reader MAY use the shapes declared in `shapes.ttl` to validate the package's
graphs against the SHACL constraints. A reader that does not perform SHACL
validation MUST still load the package normally. Specifically:

- The presence of `shapes.ttl` MUST NOT cause a reader that does not implement
  SHACL validation to fail or degrade its processing of the package.
- A reader that does not understand or implement SHACL MUST treat `shapes.ttl`
  as an opaque asset and MUST NOT hard-fail on its presence.

This preserves the forward-compatible extensibility of the format: Core-only
readers remain interoperable with Shapes-class packages.

### 4.3 Checksum verification is unconditional

Regardless of whether a reader performs SHACL validation, a reader that
encounters a manifest entry for `shapes.ttl` MUST verify the declared checksums
against the file's bytes (§2.2, requirement 3). Checksum verification applies to
all declared manifest entries and is a Core integrity requirement independent of
the Shapes conformance class.

### 4.4 SHACL validation results (informative)

When a reader does perform SHACL validation, the interpretation of constraint
violations is application-defined. This specification does not mandate whether a
shapes violation causes the reader to reject the package, emit a warning, or
expose the violation report to the consuming application. Implementers SHOULD
document their behavior.

---

## §5 Syntactic Validity

When `shapes.ttl` is present, it MUST be syntactically valid Turtle as defined
by the [W3C Turtle specification](https://www.w3.org/TR/turtle/). A reader that
parses `shapes.ttl` MUST treat a Turtle parse error as a validation error for the
Shapes conformance class. A reader that does not parse `shapes.ttl` is not
required to detect this error (§4.2).

Producers MUST NOT include a `shapes.ttl` that is not valid Turtle, regardless
of whether the consuming reader performs validation.

---

## §6 Relationship to Other Conformance Classes

The Shapes class is conformance class 4 in the CCX 3.0 class hierarchy defined
in `conformance.md` §2. It builds on the Core class (class 1) and does not
depend on the Sources (class 2) or Embeddings (class 3) classes. An
implementation MAY claim conformance to Core + Shapes without also claiming
Sources or Embeddings conformance, as permitted by `conformance.md` §3.1.

When a package claims Shapes-class conformance, the requirements in §2.2 of this
document (manifest declaration) and §2.4 of `conformance.md` (custom vocabulary
coverage, valid SHACL shapes graph) are normative membership requirements; they
are not merely RECOMMENDED.

---

## §7 Worked Example (Informative)

The following illustrates a minimal `shapes.ttl` entry in a Shapes-class package.
This example is non-normative; the normative rules are those in §2–§5 above.

**`shapes.ttl` (excerpt):**

```turtle
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:   <https://example.org/vocab/> .

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    rdfs:label "Person shape" ;
    rdfs:comment "Constrains nodes of type ex:Person." ;
    sh:property [
        sh:path ex:fullName ;
        sh:datatype <http://www.w3.org/2001/XMLSchema#string> ;
        sh:minCount 1 ;
    ] .
```

**Corresponding `manifest.json` `assets` entry:**

```json
{
  "path": "shapes.ttl",
  "media_type": "text/turtle",
  "sha256": "…",
  "sha512": "…"
}
```

The `sha256` and `sha512` values are the standard-base64 digests of the exact
bytes of the `shapes.ttl` ZIP entry (see `trust.md` §2.2).

---

## §8 Cross-References

- `ccx-3.0.md` — container format, reader contract, and security requirements
  that apply to all package entries including `shapes.ttl`.
- `manifest.md` — manifest structure, the existence constraint (§3.1), and the
  checksum verification requirement (§3.2) that govern the `shapes.ttl` manifest
  entry.
- `conformance.md` — the conformance-class hierarchy; Shapes is class 4 (§2.4).
- `vocabulary.md` — the core `ccx:` vocabulary that `shapes.ttl` SHOULD
  complement rather than duplicate.
