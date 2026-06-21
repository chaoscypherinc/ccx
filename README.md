# ccx-format

[![PyPI](https://img.shields.io/pypi/v/ccx-format.svg)](https://pypi.org/project/ccx-format/)
[![Python](https://img.shields.io/pypi/pyversions/ccx-format.svg)](https://pypi.org/project/ccx-format/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/chaoscypherinc/ccx/blob/main/LICENSE)

**CCX (Chaos Cypher eXchange)** is an open, JSON-LD-native package format for
**portable, source-backed knowledge graphs**. A `.ccx` file carries entities,
relationships, the **sources** they were extracted from, **citations** linking
claims back to those sources, and — optionally — vector **embeddings**, **SHACL
shapes**, and cryptographic **signatures**, all in a single file you can move
between tools without losing provenance.

```bash
pip install ccx-format        # then:  import ccx
```

This repository is the format **specification** (`spec/`) plus the reference
**reader + writer** (`src/ccx/`, `import ccx`). It is the format behind Lexicon
packages in [Chaos Cypher](https://github.com/chaoscypherinc/chaoscypher), but
the format and this library are **standalone and Apache-2.0** — usable with no
Chaos Cypher install.

---

## What is a `.ccx`?

A `.ccx` file is a ZIP that is, semantically, an **RDF Dataset**: a `knowledge`
default graph plus any number of namespaced **named graphs** (the single
extension mechanism). Everything is JSON-LD, self-describing, and validated
against a bundled context and JSON Schema.

```
package.ccx  (ZIP)
├── mimetype                     "application/vnd.ccx+zip" — STORED, first entry
├── manifest.json                authoritative registry (JSON-Schema validated)
├── context.jsonld               bundled JSON-LD @context (never fetched remotely)
├── knowledge.jsonld             the `knowledge` default graph: entities + relationships
├── graphs/<ns>.<name>.jsonld    namespaced named graphs (app/domain extensions)
├── sources.jsonl                source + chunk records ......................... [Sources]
├── assets/sha256/<hex>          content-addressed blobs: extracted text, vectors, files
├── shapes.ttl                   SHACL shapes ................................... [Shapes]
└── signatures/manifest.sig      detached signature over the manifest ........... [Signed]
```

**Why CCX**

- **Provenance is first-class.** Entities and relationships carry citations to
  the exact source chunk they came from — so a graph stays auditable after it
  leaves the tool that produced it.
- **Standards, not bespoke formats.** JSON-LD / RDF for the graph, W3C Web
  Annotation for citations, SHACL for shapes, SPDX for licensing, ed25519 /
  Sigstore for signing. A plain RDF/SPARQL tool can read the knowledge graph;
  app-specific data lives in clearly-namespaced graphs a neutral reader ignores.
- **Self-validating and safe.** Packages are checksummed, schema-validated, and
  read **offline + fail-closed** — no network at read time, with hardening
  against zip-bombs, path traversal, and symlink escape.

---

## Install

| Command | Adds |
|---|---|
| `pip install ccx-format` | reader + writer (only dependency: `rdflib`) |
| `pip install "ccx-format[shapes]"` | SHACL **validation** of a package against its `shapes.ttl` (`pyshacl`) |
| `pip install "ccx-format[embeddings]"` | reading Parquet embedding **sidecars** (`pyarrow`) |
| `pip install "ccx-format[signed]"` | producing + verifying **ed25519** signatures (`cryptography`) |
| `pip install "ccx-format[signed-sigstore]"` | verifying **Sigstore** signature bundles (`sigstore`) |

Detecting which conformance classes a package *claims* needs no extras; the
extras add the machinery to act on them (validate shapes, read vectors, verify
signatures). Python 3.10+.

---

## Read a package

```python
import ccx

pkg = ccx.open_package("people.ccx")        # accepts a path or raw bytes

report = pkg.validate()
print(report.ok, report.classes)            # True ('core', 'sources')
for w in report.warnings:
    print("warn:", w)

# Manifest metadata
m = pkg.manifest
print(m.name, m.package_version, m.license)  # demo/people 1.0.0 CC-BY-4.0

# Walk the graphs (the default `knowledge` graph + any named graphs)
for g in pkg.graph_documents():
    print(g.namespace, g.name, g.role)       # ccx knowledge default
    for node in g.doc["@graph"]:
        print(node["@id"], node.get("@type"))

# Sources + chunks (Core + Sources packages)
for rec in pkg.sources():
    print(rec["@id"], rec.get("@type"))       # ccx:Source / ccx:Chunk

# Or hand the whole thing to rdflib for SPARQL
dataset = pkg.dataset()                        # an rdflib.Dataset
```

Higher-class readers:

```python
pkg.shapes()                 # the shapes.ttl text, or None
pkg.shacl_validate()         # validate the graph against shapes  [needs: shapes]
pkg.embeddings()             # embedding descriptors from the manifest
pkg.read_embeddings(desc)    # read a vector sidecar               [needs: embeddings]
pkg.verify_signatures()      # offline, fail-closed                [needs: signed]
pkg.asset_bytes(path)        # raw bytes of a content-addressed asset
```

---

## Write a package

```python
import ccx

builder = ccx.PackageBuilder(
    name="demo/people",
    package_version="1.0.0",
    license="CC-BY-4.0",          # SPDX identifier
    base_iri="urn:example:",
)

# The `knowledge` default graph — plain JSON-LD
builder.add_graph("ccx", "knowledge", {
    "@graph": [
        {"@id": "urn:example:alice", "@type": "Person", "name": "Alice Smith",
         "worksFor": {"@id": "urn:example:acme"}},
        {"@id": "urn:example:acme", "@type": "Organization", "name": "Acme Corp"},
    ],
}, role="default")

# A source the graph was extracted from (stored as a content-addressed asset)
builder.add_source(
    {"@id": "urn:example:src/doc", "@type": "ccx:Source",
     "extractedBy": "my-parser/1.0"},
    text=b"Alice Smith works for Acme Corporation.",
    source_mode="derived-only",
)

data = builder.build()            # -> validated bytes (raises if non-conformant)
builder.write("people.ccx")       # or write straight to disk
```

`PackageBuilder` output is deterministic and **self-validating** — `build()`
opens and validates the bytes it produced before returning them, so you cannot
emit a non-conformant package. App- or domain-specific data goes in its own
named graph (`builder.add_graph("myapp", "settings", {...})`), keeping the
`knowledge` graph clean for neutral consumers.

**Sign a package** (offline, ed25519):

```python
private_key, public_key = ccx.generate_ed25519_keypair()   # [needs: signed]
builder.sign(private_key)        # detached signature; call last, before build()
```

---

## Command line

Installing the package puts a `ccx` command on your PATH:

```bash
ccx inspect  people.ccx          # print the manifest summary (name, version, graphs)
ccx validate people.ccx          # validate; exit non-zero + reasons if invalid
ccx pack ./my-package -o out.ccx # assemble a .ccx from a prepared directory
```

`ccx pack` expects a directory containing `manifest.json` and `knowledge.jsonld`,
with optional `graphs/<namespace>.<name>.jsonld`, `context.jsonld`, and an
`assets/` tree.

---

## Conformance classes

`validate()` reports every class a package satisfies in `report.classes`. They
are **independent capabilities**, not a linear ladder — a package can be
`Core + Sources` without embeddings or shapes.

| Class | A package qualifies when it… |
|---|---|
| **Core** | is a well-formed `.ccx`: STORED `mimetype`, schema-valid `manifest.json`, every declared file present with matching SHA-256 + SHA-512, a `knowledge` default graph, no remote `@context`. |
| **Core + Sources** | adds `sources.jsonl` with source/chunk records (offset selectors into a text asset, or inline content) and citations aligned to W3C Web Annotation. |
| **Embeddings** | declares embedding descriptors (model + dimensions), optionally with content-addressed vector sidecars. |
| **Shapes** | ships a valid SHACL `shapes.ttl`. |
| **Signed** | ships ≥1 detached signature over the manifest (ed25519 offline, or a Sigstore bundle). |

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
- **Signatures** verify **offline** and **fail closed**; checksums are
  Grover-resistant and the signature `format` field is crypto-agile, with
  post-quantum (ML-DSA / SLH-DSA) formats reserved.

---

## Repository layout

| Path | What |
|---|---|
| [`spec/`](https://github.com/chaoscypherinc/ccx/tree/main/spec) | the normative specification (Markdown, RFC-2119) |
| `src/ccx/` | the reference reader + writer (this PyPI package) |
| [`conformance/`](https://github.com/chaoscypherinc/ccx/tree/main/conformance) | fixture packages — valid + deliberately invalid — for self-testing |
| `tests/` | the test suite |

---

## License

- Reference implementation (`src/`, this package): **Apache-2.0**.
- Specification (`spec/`): **CC-BY-4.0**.

Dependencies are OSI-approved permissive; `rdflib` is the only required runtime
dependency. CCX is an open, documented format — there is no vendor lock-in, and
a `.ccx` produced by any tool is readable by any conformant reader.

Issues and discussion: <https://github.com/chaoscypherinc/ccx/issues>.
Chaos Cypher (the knowledge-graph platform CCX powers):
<https://github.com/chaoscypherinc/chaoscypher>.
