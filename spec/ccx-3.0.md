# CCX 3.0 — Core Specification

**Chaos Cypher eXchange (CCX)** is an open, JSON-LD-native package format for
portable, source-backed knowledge graphs. A CCX package is a ZIP archive that is,
semantically, an **RDF Dataset**: a `knowledge` default graph together with zero or
more namespaced named graphs.

This document defines the **Core** conformance class: the minimum set of
requirements a package must satisfy and a reader must enforce in order to
interoperate. Higher conformance classes (for example, signature verification) are
layered on top of Core and are defined in companion documents.

Companion specifications referenced here use relative names: the manifest schema
(`manifest.md`) and the trust and integrity model (`trust.md`).

---

## §1 Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and only when, they
appear in all capitals, as shown here.

Text not written with these keywords is explanatory and non-normative.

### 1.1 Terms

**Package**
: A single `.ccx` file: a ZIP archive (§3) whose entries collectively define one
  RDF Dataset (§2) plus the metadata, sources, and assets needed to interpret it
  offline.

**RDF Dataset**
: A collection of RDF graphs comprising exactly one unnamed *default graph* and
  zero or more *named graphs*, each identified by an IRI. CCX packages serialize a
  dataset as a set of JSON-LD documents declared in the manifest.

**Default graph**
: The unnamed graph of the RDF Dataset. In a CCX package this is the `knowledge`
  graph and carries the package's primary assertions. A reader that understands
  only RDF and ignores named graphs MUST still be able to load the default graph.

**Named graph**
: A graph in the dataset identified by a graph IRI. In CCX, every graph other than
  the default graph is a named graph and is declared with an explicit `namespace`
  and `name` (§4).

**First-class payload**
: A graph document that is part of the dataset proper rather than supporting
  material — that is, a graph whose triples are loaded into the default graph or a
  named graph. `knowledge.jsonld` is the REQUIRED first-class payload at Core.

**Asset**
: A binary or opaque file carried inside the package (for example, an image or a
  PDF) that is referenced by the graph but is not itself RDF. Assets are declared
  in the manifest and are checksum-protected, but are not parsed as graphs.

**Reader**
: Software that opens a package, validates it, and exposes its dataset, sources,
  and assets to a consuming application. Conformance requirements on readers are
  given in §5 and §6.

**Writer**
: Software that assembles a conformant package from graphs, assets, and metadata.

**Conformance class**
: A named, cumulative set of requirements. This document defines **Core**. A
  package or implementation that satisfies every requirement of a class is said to
  *conform* to that class.

---

## §2 Model

A `.ccx` package MUST be an RDF Dataset: a `knowledge` default graph plus zero or
more namespaced named graphs (§4).

Named graphs are the package's single extension mechanism. All extensibility —
application-specific overlays, lenses, provenance layers, and the like — is
expressed by adding named graphs; the Core model itself is not otherwise extended.

A reader that understands only RDF and ignores named graphs MUST still be able to
load the default graph. Consequently, a package MUST NOT place information that is
essential to interpreting the default graph's assertions exclusively inside a named
graph; the default graph MUST stand on its own as a usable RDF graph.

The on-disk serialization of each graph is JSON-LD. How a reader materializes the
dataset (in memory, in a triplestore, or otherwise) is out of scope: the format is
storage-agnostic and prescribes only the package bytes and the abstract dataset
they denote.

---

## §3 Container

### 3.1 Archive format

A package MUST be a ZIP archive. A reader MUST reject input that is not a
well-formed ZIP archive as a fatal error.

### 3.2 The `mimetype` entry

The first entry in the archive MUST be named `mimetype`, MUST be stored
uncompressed (ZIP method STORED), and its bytes MUST be exactly the US-ASCII string:

```
application/vnd.ccx+zip
```

This entry acts as the package's magic number: an uncompressed leading `mimetype`
member lets a consumer identify a CCX package by reading the first few bytes,
without inflating any data. This convention follows the same approach used by other
ZIP-based formats such as EPUB and ODF.

Readers MUST treat a missing, non-first, compressed, or incorrect `mimetype` entry
as a fatal error.

### 3.3 Required and optional entries

At the Core conformance class, the following entries are REQUIRED:

| Entry | Description |
| --- | --- |
| `mimetype` | The media-type magic number (§3.2). MUST be first and STORED. |
| `manifest.json` | The package manifest: metadata and the graph/asset registry, with a checksum for every declared file (see `manifest.md`). MUST be schema-valid. |
| `context.jsonld` | The bundled JSON-LD `@context` shared by the package's graphs. MUST be local; remote contexts are prohibited (§6). |
| `knowledge.jsonld` | At least one first-class payload — the default (`knowledge`) graph. |

A package MUST contain at least one first-class payload. The default graph
serialization is named `knowledge.jsonld`.

The following entries are OPTIONAL at Core. A reader MUST NOT require them, and a
reader that does not implement a given feature MUST ignore the corresponding
entries (§5).

| Entry | Description |
| --- | --- |
| `sources.jsonl` | Source records (one JSON object per line) backing the package's assertions. |
| `shapes.ttl` | SHACL (or equivalent) shapes describing or constraining the graphs. |
| `graphs/` | Directory holding additional first-class payloads — the namespaced named graphs (§4). |
| `assets/` | Directory holding declared, checksum-protected binary assets. |
| `signatures/` | Detached signatures and related material for higher (non-Core) conformance classes (see `trust.md`). |

Every entry under `graphs/` and `assets/`, and every other graph or asset the
package relies on, MUST be declared in `manifest.json` with a checksum. Files
present in the archive but not declared in the manifest are not part of the dataset
and carry no Core guarantees.

For an à-la-carte **sources-only** package, `knowledge.jsonld` is present but its
`@graph` is empty (`knowledge.md` §2.5); the evidence lives in `sources.jsonl`. A
**knowledge-only** package simply omits `sources.jsonl`.

---

## §4 Naming

### 4.1 Standard-defined payloads

Standard-defined payloads use bare names. The default graph is `knowledge` and the
source record set is `sources`. These names are defined by this specification and
MUST NOT be repurposed by applications.

### 4.2 Application graphs

Application-defined named graphs MUST be named `<namespace>.<contents>`, where
`<namespace>` identifies the producing application or domain and `<contents>`
identifies the graph's role within that namespace — for example,
`chaoscypher.lenses`.

The corresponding manifest entry declares the graph with `namespace` set to
`<namespace>` and `name` set to `<contents>`. Neither `namespace` nor `name` may
contain `/` or `..`.

### 4.3 Reserved namespaces

The `ccx` namespace is RESERVED for this specification; applications MUST NOT
declare graphs in the `ccx` namespace other than the default `knowledge` graph. The
`core` namespace SHOULD be reserved for future standard use.

To avoid collisions, applications SHOULD choose a namespace using a reverse-DNS name
(for example, `com.example.overlays`) or a prefix registered with the CCX registry.

### 4.4 The default graph entry

The default graph MUST be declared in the manifest with:

- `namespace: "ccx"`
- `name: "knowledge"`

and SHOULD additionally carry `role: "default"`. The reference writer always emits
`role: "default"`, and producers SHOULD do the same. However, a reader MUST treat
the `ccx`/`knowledge` graph as the default graph whether or not `role: "default"`
is present — the `namespace`/`name` pair is the authoritative identifier.

A reader identifies the default graph by this declaration and maps it to the RDF
Dataset's unnamed default graph; every other declared graph is mapped to a named
graph whose IRI is derived from its `namespace` and `name`.

---

## §5 Reader contract

A reader MUST:

1. Read the default graph (§2, §4.4) and any namespace or feature it understands.
2. Ignore namespaces and features it does not understand, rather than failing.
3. Verify the checksum of every declared graph and asset before relying on its
   contents, using the digests recorded in `manifest.json` (see `trust.md` for the
   integrity model and digest algorithms).

A reader MUST NOT hard-fail on an unrecognized or malformed **extension** graph (a
named graph in an application namespace). When such a graph cannot be loaded or is
not understood, the reader MUST surface a warning and continue, making the rest of
the package — including the default graph — available to the application.

A reader MUST hard-fail only on **Core integrity** violations. The following are
fatal errors:

- a missing, non-first, compressed, or incorrect `mimetype` entry (§3.2);
- a missing or schema-invalid `manifest.json` (§3.3);
- a checksum mismatch between a declared file and its manifest digest (§5.3);
- an unsafe archive — decompression bomb, path traversal, absolute path, or
  symlink escape (§6);
- any attempt to fetch a remote JSON-LD `@context` or `@import` at read time (§6).

A missing required Core entry (`context.jsonld`, the default graph, or a declared
file that is absent from the archive) is likewise a fatal error: the package does
not conform to Core.

Conditions that compromise interoperability but not Core integrity — for example, a
`ccx_version` the reader does not recognize, or the absence of a declared license —
SHOULD be surfaced as warnings rather than fatal errors.

---

## §6 Security

A reader processes untrusted input and MUST defend against hostile packages.

**Decompression ("zip bomb") attacks.** A reader MUST bound both the number of
archive entries and the total uncompressed size it will process, and MUST also
bound the uncompressed size of any single entry. A reader MUST reject an archive
that exceeds these bounds rather than attempting to inflate it. (The reference
reader caps entry count, per-entry uncompressed size, and total uncompressed size;
see `trust.md`.)

**Path traversal and absolute paths.** A reader MUST reject any entry whose name is
an absolute path, contains a `..` path segment, or otherwise resolves outside the
package. Both POSIX (`/`) and Windows (`\`, drive-letter) forms MUST be treated as
unsafe.

**Symlink escape.** A reader MUST reject archive entries that are symbolic links.

**Remote context fetching.** A reader MUST NOT fetch a remote JSON-LD `@context` or
`@import` at read time. Every `@context` a package relies on MUST be bundled within
the package (typically as `context.jsonld`). A package whose JSON-LD references a
remote `@context` or `@import` (an `http://` or `https://` value, at the top level,
within `@graph`, or in any nested node-scoped context) MUST be rejected. This both
prevents network-dependent and non-reproducible reads and closes a server-side
request forgery vector.

These defenses MUST be applied before any graph is parsed, and the network MUST
remain unreachable for the duration of a read.

---

## §7 Implementation status (non-normative)

> Implementation status: Core — enforced by the reference reader + writer; conformance fixtures present.

---

## Appendix A — IANA media type registration template (`application/vnd.ccx+zip`)

The following is the registration template for the CCX media type, suitable for
submission to IANA.

```
Type name: application

Subtype name: vnd.ccx+zip

Required parameters: N/A

Optional parameters: N/A

Encoding considerations:
  binary. A CCX file is a ZIP archive and MUST be treated as binary data.

Security considerations:
  See §6 of the CCX 3.0 Core specification. CCX is a container format for
  untrusted, third-party content; readers must defend against decompression
  ("zip bomb") attacks via bounded entry counts and bounded total and per-entry
  uncompressed size; against path traversal, absolute paths, and symlink escape
  in archive entry names; and MUST NOT fetch remote JSON-LD @context or @import
  references at read time (a network-dependence and SSRF concern). Declared graphs
  and assets are integrity-protected by checksums recorded in the manifest.

Interoperability considerations:
  The first archive entry is an uncompressed (STORED) member named "mimetype"
  whose bytes are exactly "application/vnd.ccx+zip", which serves as the magic
  number (see below). Consumers that ignore named graphs can still load the
  default graph.

Published specification:
  CCX 3.0 Core specification (this document).

Applications that use this media type:
  Tools that produce or consume portable, source-backed knowledge graphs,
  including the reference "ccx-format" reader and writer.

Fragment identifier considerations: N/A

Additional information:
  Magic number(s):
    The archive's first entry is a STORED (uncompressed) ZIP member named
    "mimetype" whose content is exactly the US-ASCII bytes
    "application/vnd.ccx+zip". As a ZIP archive, a CCX file also begins with the
    ZIP local-file-header signature (PK\x03\x04).
  File extension(s): .ccx
  Macintosh file type code(s): N/A

Person & email address to contact for further information:
  The CCX maintainers.

Intended usage: COMMON

Restrictions on usage: N/A

Author/Change controller: The CCX specification maintainers.
```
