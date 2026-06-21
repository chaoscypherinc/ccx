# CCX 3.0 Conformance Fixtures

Canonical sample packages for the CCX 3.0 conformance classes. Regenerate with:

```
python scripts/emit_conformance.py
```

## Valid

- `valid/core-minimal.ccx` — minimal Core package (the `knowledge` default graph).
- `valid/core-with-app-graph.ccx` — Core plus a namespaced application graph.
- `valid/sources-minimal.ccx` — Core + Sources: a `sources.jsonl` index, a
  content-addressed extracted-text asset, and a `source_mode`.
- `valid/sources-inline-chunk.ccx` — Core + Sources with an inline-`content` chunk
  (the graduated fallback; no text asset) plus chunking provenance.
- `valid/sources-only.ccx` — à-la-carte sources-only package: an empty `knowledge`
  graph + `sources.jsonl`.
- `valid/embeddings-minimal.ccx` — Embeddings: a manifest embedding descriptor and
  a content-addressed vector sidecar.
- `valid/signed-minimal.ccx` — Signed-shaped: a declared + checksummed
  `signatures/manifest.sig` plus a manifest `signatures` entry (placeholder bytes).
- `valid/shapes-minimal.ccx` — Shapes: a SHACL `shapes.ttl`.

## Invalid

`invalid/*.ccx` — packages a Core reader MUST reject, one defect each: bad checksum,
missing mimetype, a compressed (non-STORED) mimetype, missing / invalid / malformed
manifest, remote `@context` (in the knowledge graph or in the context file), corrupt
context, path traversal, and a declared signature asset that is absent
(`signed-missing-sig`).

These are produced by `tests/fixtures.py`. See `spec/conformance.md` for the
conformance classes and how each fixture maps to them.

> Citation-anchor validity and cryptographic signature verification are
> higher-class reader concerns; the Core reference reader does not enforce them, so
> the Sources/Signed fixtures here are structurally valid Core packages.
