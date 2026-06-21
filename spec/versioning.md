# CCX Versioning and Compatibility

**Document:** CCX 3.0, `versioning.md`
**Status:** Normative Draft
**License:** CC-BY-4.0

Normative keywords in this document follow RFC 2119 / RFC 8174. The key words
**MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**,
**SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted
as described in those RFCs.

---

## 1. Scope

This section defines the two independent version fields carried by a CCX package,
the compatibility contract that governs how readers handle version differences, and
the process by which the specification itself is versioned.

---

## 2. Two Independent Versions

### 2.1 Format version (`ccx_version`)

`ccx_version` identifies the **version of the CCX format** — the wire encoding,
manifest schema, required fields, JSON-LD context, and the compatibility rules
described in this document. It is a property of the specification, not of any
individual package.

`ccx_version` is governed by Semantic Versioning 2.0.0 (semver). Its value is a
string of the form `"MAJOR.MINOR"` (patch is omitted from the wire value because
patch releases carry no wire-format change; see Section 3.3).

Every conforming package MUST carry a `ccx_version` field in its manifest. A
reader MUST reject any package that does not carry this field.

### 2.2 Package version (`package_version`)

`package_version` identifies the **version of the content** that a specific
package carries — the knowledge graph, its sources, its assets, and any
package-level metadata chosen by its author. It is a property of the package, not
of the format.

`package_version` is also semver-governed, but its versioning policy is entirely
the responsibility of the package author. Format readers MUST NOT interpret or
validate `package_version` beyond confirming it is a valid semver string when
present. `package_version` is OPTIONAL; its absence does not affect format
conformance.

### 2.3 Distinction

These two versions serve orthogonal purposes and MUST NOT be conflated:

| Field | Answers | Governed by |
|---|---|---|
| `ccx_version` | "Which edition of the CCX format is this?" | This specification |
| `package_version` | "Which revision of the content is this?" | The package author |

A package author bumping content from v1.2 to v2.0 does so by changing
`package_version`; the `ccx_version` remains unchanged unless the package was
re-encoded against a newer format revision.

---

## 3. Compatibility Contract

This section states the normative contract between format versions and
implementations. "Reader" means any conforming software that reads `.ccx`
packages; "writer" means any software that produces them.

### 3.1 Minor version — additive, backward-compatible

A MINOR version increment signals an additive, backward-compatible change to the
format. New optional fields or named-graph types MAY be introduced; no existing
field is removed or given an incompatible meaning.

- A reader MUST accept a package whose `ccx_version` minor number is higher than
  the minor number the reader was written against, provided the major numbers
  match.
- A reader MUST ignore any field, graph, or extension it does not recognize when
  the major numbers match. It MUST NOT treat the presence of an unrecognized
  addition as an error.
- A writer MUST NOT use features introduced in a minor version without setting
  `ccx_version` to at least that minor version.

### 3.2 Major version — potentially breaking

A MAJOR version increment MAY introduce changes that are not backward-compatible:
fields may be removed, renamed, or given incompatible semantics, and the
manifest schema may change structurally.

- A reader MAY refuse to open a package whose `ccx_version` major number it does
  not support. If it refuses, it MUST report a clear, actionable error identifying
  the unsupported major version.
- A reader MUST NOT silently misread a package whose major version it does not
  support. Partial, best-effort interpretation of an unsupported major version is
  prohibited unless the reader explicitly documents the scope of its partial
  support and surfaces a non-fatal warning to the caller.

### 3.3 Patch version — editorial only

A PATCH version increment is reserved for editorial corrections to the
specification text (clarifications, typo fixes, normative-language tightening)
that carry no change to the wire format or to reader/writer behavior.

- The `ccx_version` wire value omits the patch component. Packages always carry
  a two-part version string (e.g., `"3.0"`), never three parts.
- Readers MUST NOT reject a package solely because it was produced against a
  different patch level of the same MAJOR.MINOR version.

---

## 4. Current Version

This specification defines **CCX format version 3.0**.

> Implementation status: ccx_version = "3.0" is set by the reference library (ccx.constants.CCX_VERSION).

---

## 5. Changelog and Specification Versioning

The specification is versioned in-repository. The authoritative source for any
format version is the tagged commit in the canonical repository that introduced
that version.

A public changelog SHOULD accompany each format version. The changelog SHOULD
document, for each MAJOR and MINOR bump:

- the motivation for the change;
- a summary of additions (MINOR) or breaking changes (MAJOR);
- migration guidance for existing readers and writers.

PATCH releases SHOULD include a brief errata note identifying the sections
corrected.

Cross-references to other sections of this specification use relative paths of the
form `./filename.md §N` (e.g., `./manifest.md §3.1`). Section numbers within each
file are considered stable across PATCH releases and SHOULD be considered stable
across MINOR releases unless a section is materially restructured.
