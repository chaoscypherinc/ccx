# CCX 3.0 — Sources and Citations

This module specifies the **Core + Sources** conformance class: the
`sources.jsonl` records that carry source metadata, extraction provenance, and
citation anchors, and the rules that bind those records to content-addressed
text assets and to citations made from the `knowledge` graph. The container,
the manifest, and the package-wide security rules are specified in
[`ccx-3.0.md`](./ccx-3.0.md); the asset registry and the `source_mode` field are
specified in [`manifest.md`](./manifest.md); the `ccx:` terms referenced here are
defined in [`vocabulary.md`](./vocabulary.md). The normative membership rule for
this class is in [`conformance.md`](./conformance.md) §2.2.

Normative keywords (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**,
**REQUIRED**, **OPTIONAL**) are to be interpreted as described in RFC 2119 and
RFC 8174 when, and only when, they appear in all capitals.

> Implementation status: ENFORCED — the reference reader grants the `sources`
> class via `validate()`; writer support via `PackageBuilder.add_source`;
> conformance fixtures present.

## 1. Role in the package

1.1. A package conforms to the **Core + Sources** class when it satisfies every
Core requirement (see [`conformance.md`](./conformance.md) §2.1) and, in
addition, every requirement of this module. The Sources class adds the evidence
layer: the documents a knowledge graph was extracted from, the provenance of
that extraction, and the anchors that let any claim in the graph point back to
the exact passage, region, or timecode that supports it.

1.2. The evidence layer is carried by three pieces working together:

- **`sources.jsonl`** (§2) — one JSON object per line, each describing a source
  or a chunk of a source.
- **Content-addressed text assets** (§4) — the full extracted text of each
  source, stored once under `assets/sha256/<hex>` and declared in the manifest.
- **Citation anchors** (§6) — W3C Web Annotation selectors and Media Fragments
  URIs that locate a passage *inside* a source or its extracted text. Selectors
  are the RECOMMENDED, canonical form; inline `content` is the permitted fallback
  where no contiguous full text is available (§4.3).

1.3. The source/citation vocabulary terms used by these records — `ccx:Source`,
`ccx:Chunk`, `ccx:Citation`, `ccx:selector`, `ccx:sourceMode`, and
`ccx:extractedBy` — are defined normatively in
[`vocabulary.md`](./vocabulary.md). This module references those terms by name
and specifies how the records that use them are laid out and validated; it does
not redefine them.

## 2. The `sources.jsonl` file

2.1. **Location.** A Core + Sources package **MUST** contain exactly one ZIP
entry named `sources.jsonl` at the package root. Like every other declared file,
it **MUST** be registered in the manifest's asset registry with verified
checksums (see [`manifest.md`](./manifest.md) §7 and §3.2).

2.2. **Encoding and structure.** `sources.jsonl` **MUST** be a UTF-8-encoded
[JSON Lines](https://jsonlines.org/) file: a sequence of records separated by
the line-feed character (`U+000A`), where **each line is independently a single,
complete, well-formed JSON object**. A record **MUST NOT** span multiple lines,
and a line **MUST NOT** contain more than one JSON object. The file **MAY** end
with a trailing newline.

2.3. **Line-by-line parsing.** A reader of the Sources class **MUST** parse
`sources.jsonl` line by line, treating each non-empty line as an independent JSON
document. A reader **MUST NOT** require the file as a whole to be a single JSON
value (it is not a JSON array). Readers **SHOULD** ignore blank lines. Because
each record is self-contained, a consumer can stream the file and process,
index, or reject individual records without holding the entire file in memory.

2.4. **Record kinds.** Each record describes either a whole source or a chunk of
a source, distinguished by its `@type`:

- a **source record** (`@type` includes `ccx:Source`) describes one source
  document: its identity, its media mode (§3), its extraction provenance (§5),
  and a reference to its extracted-text asset (§4);
- a **chunk record** (`@type` includes `ccx:Chunk`) describes a contiguous
  region of a source's extracted text, expressed **either** as an offset selector
  (§6) into that source's text asset (the RECOMMENDED, scalable form) **or** as
  inline `content` (a string) when no contiguous full text is available (§4.3).

2.5. **Source identity.** Every source record **MUST** carry a stable `@id` so
that chunk records, citations in the `knowledge` graph, and per-source license
or provenance metadata can reference it. A chunk record **MUST** reference the
source it belongs to by that `@id`. Identity rules follow
[`knowledge.md`](./knowledge.md) §4: an `@id` denotes the same source across
every record and package in which it appears.

2.6. **Per-source licensing.** A source record **MAY** carry a `license` field
(an SPDX identifier) that overrides the package-level `license` for that source
only, as described in [`manifest.md`](./manifest.md) §5.4. Where no override is
present, the package-level license applies.

## 3. Source media mode

3.1. Every source's media mode **MUST** be recorded in the manifest asset entry
for that source as the `source_mode` field (see [`manifest.md`](./manifest.md)
§7), whose value **MUST** be exactly one of:

- **`embedded`** — the original source bytes travel inside the package as a
  checksummed asset. The evidence is present and verifiable offline.
- **`referenced`** — only a locator (such as a URL or other stable identifier),
  a checksum of the original, and descriptive metadata travel; the original
  bytes are not shipped. The evidence is absent but, in principle, fetchable and
  verifiable against the recorded checksum.
- **`derived-only`** — only the derived artifacts travel: the extracted text and
  the chunks and citations that index it. Neither the original bytes nor a
  retrieval locator are shipped. The evidence beyond the extracted text is
  absent.

3.2. The media mode tells a consumer, for each source, **whether the underlying
evidence is present (`embedded`), fetchable (`referenced`), or absent
(`derived-only`)**. A consumer **MUST NOT** assume that the original source bytes
are available unless `source_mode` is `embedded`.

3.3. The vocabulary term for this concept is `ccx:sourceMode`
([`vocabulary.md`](./vocabulary.md)); a source record **MAY** additionally
restate the mode in-record using that term, but the authoritative value is the
`source_mode` recorded on the manifest asset entry. Where both appear they
**MUST** agree.

3.4. A `referenced` or `derived-only` source **MAY** still ship a
content-addressed *extracted-text* asset (§4); the media mode classifies the
*original* source material, not the derived text. A `derived-only` source
**MUST NOT** ship the original source bytes as an asset.

## 4. Extracted text as a content-addressed asset

4.1. The full extracted text of a source **MUST** be stored as a
content-addressed asset under `assets/sha256/<hex>`, where `<hex>` is the SHA-256
digest of the asset bytes encoded as defined in [`ccx-3.0.md`](./ccx-3.0.md).
The asset **MUST** be declared and checksummed in the manifest asset registry
like every other asset (see [`manifest.md`](./manifest.md) §3.1–§3.2 and §7).

4.2. A source record **MUST** reference its extracted-text asset (for example by
the asset's content-addressed path or by its SHA-256 digest) so that chunk and
citation selectors can be resolved against a known, integrity-protected
byte stream.

**4.3. Chunk text: offset selectors (canonical) or inline content (fallback).** A
chunk's text MAY be carried two ways: (a) **RECOMMENDED** — an offset selector
(§6) into a content-addressed text asset (§4), so overlapping chunks share one
canonical copy; or (b) inline `content` (a string) when no contiguous full text
is retained (e.g. derived-only or chunk-only sources). A **Sources-class reader
MUST handle both**: resolve selectors against the text asset *and* read inline
`content`; it **MUST NOT** silently drop inline `content`. When both a selector
and inline `content` are present, the selector's target is authoritative. The
rationale below still recommends the selector form wherever full text exists.

> Rationale (non-normative): chunks routinely overlap — a sliding window over a
> document produces thousands of chunks that each re-cover the text of their
> neighbours. Inlining the text into every record would duplicate every
> overlapping region many times over, bloating the package and creating
> divergent copies of the same passage. Storing the text once as a
> content-addressed asset and pointing into it with offsets keeps the package
> compact and keeps every chunk and citation anchored to one canonical,
> checksum-verified copy of the text.

## 5. Extraction provenance

5.1. The extraction provenance of each source — the parser, OCR engine, speech
transcription tool, or other process that produced the derived text — **MUST**
be recorded per source using the `ccx:extractedBy` term defined in
[`vocabulary.md`](./vocabulary.md). The recorded value **MUST** identify both the
**tool name and its version** (for example `"pdfplumber/0.11.4"` or
`"whisper/large-v3"`), so that a consumer can detect when derived text was
produced by a tool or version it does not trust, or re-run extraction to compare.

5.2. A source record **SHOULD** also record when extraction was performed, as an
`extractedAt` timestamp that **SHOULD** be an RFC 3339 / ISO 8601 date-time in
UTC (consistent with [`manifest.md`](./manifest.md) §5.3).

5.3. Where a source's derived text was produced by more than one tool in a
pipeline (for example OCR followed by layout reconstruction), `ccx:extractedBy`
**MAY** carry an ordered list of tool identifiers describing that pipeline.

**5.4. Chunking provenance.** A source record MAY carry a `chunking` object
recording how its chunks were produced: `strategy` (e.g. `recursive_character`),
`target_size`, `overlap`, `min_size`, `max_size` (character counts), `separators`
(array), and `normalize` (boolean); implementations MAY add their own fields.
This provenance is **not recomputable** from the resulting chunks, so it is
carried, not dropped. It is plain JSON Lines metadata on the source record (no
`ccx:` vocabulary term is required).

## 6. Citation anchors

6.1. **Standard selectors only.** Citation anchors — the references that locate a
specific passage, page region, timecode range, or image region within a source —
**MUST** be expressed using the
[W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
selectors and/or
[Media Fragments URIs](https://www.w3.org/TR/media-frags/). **CCX MUST NOT define
its own bespoke anchor scheme**, and a producer **MUST NOT** introduce a
proprietary anchor syntax in place of these standards.

6.2. A citation anchor is carried on a chunk or citation record via the
`ccx:selector` term ([`vocabulary.md`](./vocabulary.md)). Its value **MUST** be a
Web Annotation selector (or an array of selectors, refining one another), each of
a standard selector type.

6.3. **Offsets into extracted text.** An anchor into the extracted text of a
source **MUST** use a standard Web Annotation offset selector — typically a
`TextPositionSelector` carrying integer `start` and `end` character offsets — to
identify a region of the content-addressed text asset (§4). The `start` and
`end` values are positions in that asset's text; this offset-selector form is the
RECOMMENDED, canonical anchor, with inline `content` (§4.3) as the permitted
fallback where no contiguous full text is available. A `TextQuoteSelector`
**MAY** accompany a position selector for robustness, but the position selector
is authoritative for resolution against the text asset.

6.4. **Anchors into original media.** Where the citation points into original
media rather than into the extracted text, the appropriate standard selector or
fragment **MUST** be used:

- a **page and region of a PDF or image** — a Media Fragments URI and/or a
  `FragmentSelector`, optionally refined by an `SvgSelector` for an arbitrary
  region;
- an **audio or video timecode range** — a Media Fragments temporal fragment
  (for example `#t=12.5,18.0`), carried as a `FragmentSelector`;
- a **rectangular image region** — a Media Fragments spatial fragment or an
  `SvgSelector`.

6.5. **Malformed anchors are invalid.** A reader of the Sources class **MUST**
reject a record whose citation anchor does not conform to W3C Web Annotation
selector syntax or Media Fragments URI syntax. The Core reference reader does not
parse anchors, so the Core conformance suite ships no rejection fixture for a
malformed anchor; a Sources-class implementation validates anchors against its own
fixtures (see [`conformance.md`](./conformance.md) §4.2).

6.6. **Citations from the knowledge graph.** A `ccx:Citation` attached to a
`ccx:Relationship` or to a node in the `knowledge` graph (see
[`knowledge.md`](./knowledge.md) §5.4) references the source or chunk record it
draws on by that record's `@id`, and the selector that pins the exact supporting
region lives on the cited chunk/citation record here. This keeps the knowledge
graph compact while making every claim traceable to a checksum-verified region
of evidence. A `ccx:Citation` is modeled on the W3C Web Annotation model
(`oa:Annotation`): the selector (§6.1–§6.4) is the annotation target;
`ccx:confidence` and `ccx:extractionMethod` (`vocabulary.md`) are the only
CCX-specific additions.

## 7. Example (informative)

The following two lines illustrate a `sources.jsonl`. The first line is a
**source record**: it declares the source's identity, references its extracted
text by the content-addressed asset path, and records extraction provenance with
`ccx:extractedBy`. The second line is a **chunk/citation record** that anchors a
passage with a Web Annotation `TextPositionSelector` giving `start`/`end`
character offsets into that same text asset — no source text is copied into the
record. Each line is independently valid JSON; they are shown wrapped here for
readability but **MUST** each occupy a single physical line in the file.

```json
{"@id": "ccx:source/handbook", "@type": "ccx:Source", "title": "Employee Handbook", "extractedText": "assets/sha256/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", "extractedBy": "pdfplumber/0.11.4", "extractedAt": "2026-06-01T09:30:00Z"}
{"@id": "ccx:source/handbook#chunk-12", "@type": "ccx:Chunk", "source": {"@id": "ccx:source/handbook"}, "ccx:selector": {"type": "TextPositionSelector", "source": "assets/sha256/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", "start": 1840, "end": 2105}}
```

In this example the source's media mode is recorded on the corresponding
manifest asset entry as `source_mode` (here it would be `embedded` if the
original PDF also ships, or `derived-only` if only the extracted text ships). The
chunk's `TextPositionSelector` resolves against the content-addressed text asset
identified by `source`, locating characters 1840–2105 of that text. A
`ccx:Citation` in `knowledge.jsonld` can reference `ccx:source/handbook#chunk-12`
to back a relationship with this exact, checksum-verified passage.

## 8. Cross-references

- [`ccx-3.0.md`](./ccx-3.0.md) — container model, reader contract, security, and
  checksum/digest encoding.
- [`manifest.md`](./manifest.md) — the asset registry, the `source_mode` field,
  and per-source `license` overrides.
- [`knowledge.md`](./knowledge.md) — the `knowledge` graph and how citations
  attach to relationships and nodes.
- [`vocabulary.md`](./vocabulary.md) — the normative definitions of `ccx:Source`,
  `ccx:Chunk`, `ccx:Citation`, `ccx:selector`, `ccx:sourceMode`, and
  `ccx:extractedBy`.
- [`conformance.md`](./conformance.md) — the normative Core + Sources membership
  rule (§2.2) and the Sources fixture map (§4.2).
