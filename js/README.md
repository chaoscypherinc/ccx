# @chaoscypherinc/ccx-format

[![npm](https://img.shields.io/npm/v/@chaoscypherinc/ccx-format.svg)](https://www.npmjs.com/package/@chaoscypherinc/ccx-format)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/chaoscypherinc/ccx/blob/main/LICENSE)

The Apache-2.0 **TypeScript reference reader** for **CCX 3.0** — parity-tested
against the Python `ccx-format` reader on the shared conformance fixtures.

**CCX (Chaos Cypher eXchange)** is an open, JSON-LD-native package format for
**portable, source-backed knowledge graphs**. A `.ccx` file is a ZIP that is,
semantically, an **RDF Dataset**: a `knowledge` default graph plus any number of
namespaced named graphs. It carries entities, relationships, the **sources** they
were extracted from, **citations** linking claims back to those sources, and —
optionally — vector **embeddings**, **SHACL shapes**, and cryptographic
**signatures**, all in a single file you can move between tools without losing
provenance.

This package is a **reader/validator** (read + validate + inspect). To *write*
`.ccx` files, use the Python `ccx-format` package (`pip install ccx-format`).

```bash
npm i @chaoscypherinc/ccx-format
```

Node ≥ 18. Self-contained: the only runtime dependencies are `jszip` and `ajv`.

---

## Read and validate a package

```ts
import { readFileSync } from "node:fs";
import { openPackage } from "@chaoscypherinc/ccx-format";

// openPackage takes raw bytes (Uint8Array). Read the file however you like.
const pkg = await openPackage(readFileSync("people.ccx"));

const report = await pkg.validate();
console.log(report.ok, report.classes); // true [ 'core', 'sources' ]
for (const w of report.warnings) console.log("warn:", w);

// Manifest metadata
const m = pkg.manifest;
console.log(m.name, m.packageVersion, m.license); // demo/people 1.0.0 CC-BY-4.0

// Walk the graphs (the default `knowledge` graph + any named graphs)
for (const g of await pkg.graphDocuments()) {
  console.log(g.namespace, g.name, g.role); // ccx knowledge default
  const doc = g.doc as { "@graph"?: { "@id": string; "@type"?: unknown }[] };
  for (const node of doc["@graph"] ?? []) {
    console.log(node["@id"], node["@type"]);
  }
}

// Sources + chunks (Core + Sources packages)
for (const rec of await pkg.sources()) {
  console.log(rec["@id"], rec["@type"]); // ccx:Source / ccx:Chunk
}
```

Higher-class accessors:

```ts
await pkg.context();           // the parsed bundled JSON-LD @context
await pkg.shapes();            // the shapes.ttl text, or null
pkg.embeddings();              // embedding descriptors from the manifest
await pkg.verifySignatures();  // offline, fail-closed ed25519 verification
await pkg.assetBytes(path);    // raw bytes of a content-addressed asset
await pkg.computeStats();      // { nodeCount, edgeCount, sourceCount }
```

### Error handling

`openPackage` rejects unsafe archives (zip bomb, path traversal, symlink escape,
bad ZIP) and missing/malformed/schema-invalid manifests. Recoverable validation
problems are reported on `report.errors` (with `report.ok === false`) rather than
thrown.

```ts
import { openPackage, CcxValidationError, CcxSecurityError } from "@chaoscypherinc/ccx-format";

try {
  const pkg = await openPackage(bytes);
  const report = await pkg.validate();
  if (!report.ok) console.error("invalid:", report.errors);
} catch (err) {
  if (err instanceof CcxSecurityError) console.error("unsafe package:", err.message);
  else if (err instanceof CcxValidationError) console.error("malformed package:", err.message);
  else throw err;
}
```

---

## Conformance classes

`validate()` reports every class a package satisfies in `report.classes`. They
are **independent capabilities**, not a linear ladder — a package can be
`core + sources` without embeddings or shapes.

| Class | A package qualifies when it… |
|---|---|
| **core** | is a well-formed `.ccx`: STORED `mimetype`, schema-valid `manifest.json`, every declared file present with matching SHA-256 + SHA-512, a `knowledge` default graph, no remote `@context`. |
| **sources** | adds `sources.jsonl` with source/chunk records (offset selectors into a text asset, or inline content) and citations aligned to W3C Web Annotation. |
| **embeddings** | declares embedding descriptors (model + dimensions), optionally with content-addressed vector sidecars. |
| **shapes** | ships a valid SHACL `shapes.ttl`. |
| **signed** | ships ≥ 1 detached signature over the manifest (ed25519, verified offline). |

Full normative requirements (RFC-2119) are in the
[specification](https://github.com/chaoscypherinc/ccx/tree/main/spec).

---

## Security & hardening

The reader is built to consume **untrusted** packages:

- **No network at read time** — remote `@context` / `@import` references are
  rejected; the bundled `context.jsonld` is authoritative.
- **Decompression bounds** — entry-count, per-entry, and total-uncompressed
  limits guard against zip-bombs.
- **Path safety** — path traversal, absolute paths, and symlink entries are
  rejected.
- **Integrity** — every declared file's SHA-256 **and** SHA-512 are verified.
- **Signatures** verify **offline** and **fail closed**; the signature `format`
  field is crypto-agile, with post-quantum (ML-DSA / SLH-DSA) formats reserved.

---

## License

**Apache-2.0.** This is the TypeScript reference reader for the CCX format, the
second independent implementation alongside the Python `ccx-format` reader and
verified against it on the shared conformance fixtures. CCX is an open, documented
format — there is no vendor lock-in, and a `.ccx` produced by any tool is readable
by any conformant reader.

Issues and discussion: <https://github.com/chaoscypherinc/ccx/issues>.
