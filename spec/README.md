# CCX 3.0 Specification

The normative specification for **CCX (Chaos Cypher eXchange)** — an open,
JSON-LD-native package format for portable, source-backed knowledge graphs.
A `.ccx` file is a ZIP that is, semantically, an RDF Dataset.

- **Status:** Draft. **License:** CC-BY-4.0. **Format version:** `ccx_version` 3.0.
- Normative keywords follow RFC 2119 / RFC 8174 (see `ccx-3.0.md` §Conventions).

## Reading order

1. `ccx-3.0.md` — model, container, naming, reader contract, security (start here).
2. `manifest.md` — the manifest.
3. `knowledge.md` — the knowledge graph (JSON-LD, IRIs, edges).
4. `vocabulary.md` — the `ccx:` vocabulary.
5. `versioning.md` — version + compatibility rule.
6. `conformance.md` — conformance classes and the fixture suite.
7. Class modules: `sources.md`, `embeddings.md`, `trust.md`, `shapes.md`.

## Conformance classes (summary)

| Class | Adds |
|-------|------|
| Core | mimetype + manifest + context + `knowledge` default graph + named graphs + assets + checksums |
| Core + Sources | `sources.jsonl` + media modes + Web Annotation citation anchors |
| Embeddings | embedding descriptor + content-addressed vector sidecar |
| Shapes | SHACL `shapes.ttl` |
| Signed | Sigstore-style signature over the manifest |

See `conformance.md` for normative membership rules.

## How to cite

Cite by file and section: "CCX 3.0, `ccx-3.0.md` §4.2". Section numbers are stable.
