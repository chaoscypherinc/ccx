"""Higher-conformance-class detection and validation over an opened package.

Core is validated in `package.py`. Each checker here takes an opened
``CCXPackage`` and returns ``(present, issues)``:

- ``present`` — the class's artifacts are in the package (so the package is
  *claiming* the class).
- ``issues`` — empty when the package conforms to the class; otherwise a list of
  human-readable problems.

A class is granted (added to ``ValidationReport.classes``) only when it is
present and has no issues. Per the reader contract, a present-but-malformed
extension does **not** fail Core validation — it surfaces warnings and is simply
not granted the class. Absence is never an error.
"""

from __future__ import annotations

import json

from .constants import SHAPES_PATH, SOURCE_MODES, SOURCES_PATH


def check_sources(pkg) -> tuple[bool, list[str]]:
    """Core + Sources: sources.jsonl is valid JSON Lines, media modes are valid,
    and offset selectors stay within their referenced text asset."""
    if not pkg.container.has(SOURCES_PATH):
        return False, []
    issues: list[str] = []

    raw = pkg.container.read(SOURCES_PATH).decode("utf-8")
    records: list[dict] = []
    for n, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            issues.append(f"sources.jsonl line {n} is not valid JSON: {exc}")

    for asset in pkg.manifest.raw.get("assets", []):
        mode = asset.get("source_mode")
        if mode is not None and mode not in SOURCE_MODES:
            issues.append(
                f"asset {asset.get('path')!r} has invalid source_mode {mode!r} "
                f"(expected one of {', '.join(SOURCE_MODES)})"
            )

    text_len: dict[str, int] = {}
    for rec in records:
        selector = rec.get("selector")
        if not isinstance(selector, dict):
            continue
        start, end = selector.get("start"), selector.get("end")
        if start is None and end is None:
            continue  # a non-offset selector (e.g. a Media Fragment) — not range-checked
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
            issues.append(f"record {rec.get('@id')!r}: invalid offset selector (start/end)")
            continue
        text_ref = rec.get("text")
        if isinstance(text_ref, str) and pkg.container.has(text_ref):
            if text_ref not in text_len:
                text_len[text_ref] = len(pkg.container.read(text_ref).decode("utf-8"))
            if end > text_len[text_ref]:
                issues.append(
                    f"record {rec.get('@id')!r}: selector end {end} exceeds "
                    f"text length {text_len[text_ref]} for {text_ref!r}"
                )

    return True, issues


def check_shapes(pkg) -> tuple[bool, list[str]]:
    """Shapes: shapes.ttl is present, parses as Turtle, and declares at least one
    SHACL NodeShape or PropertyShape. (Parsing uses rdflib, a core dependency;
    validating the data *against* the shapes is the optional `shapes` extra — see
    CCXPackage.shacl_validate.)"""
    if not pkg.container.has(SHAPES_PATH):
        return False, []
    import rdflib

    text = pkg.container.read(SHAPES_PATH).decode("utf-8")
    graph = rdflib.Graph()
    try:
        graph.parse(data=text, format="turtle")
    except Exception as exc:  # noqa: BLE001 - any parse failure is a class issue
        return True, [f"shapes.ttl is not valid Turtle: {exc}"]
    sh = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    has_shape = any(graph.triples((None, rdflib.RDF.type, sh.NodeShape))) or any(
        graph.triples((None, rdflib.RDF.type, sh.PropertyShape))
    )
    if not has_shape:
        return True, ["shapes.ttl declares no SHACL NodeShape or PropertyShape"]
    return True, []


def check_embeddings(pkg) -> tuple[bool, list[str]]:
    """Embeddings: each manifest embedding descriptor is well-formed, and every
    `included` descriptor points at a declared, present sidecar asset.

    (The descriptor's required `model`/`dimensions` and `dimensions >= 1` are
    enforced structurally by the manifest JSON Schema at Core; this checker adds
    the semantic rule that an included sidecar must actually be in the package.)
    """
    descriptors = pkg.manifest.raw.get("embeddings")
    if not descriptors:
        return False, []
    issues: list[str] = []
    asset_paths = {a.path for a in pkg.manifest.assets}
    for i, descriptor in enumerate(descriptors):
        if not isinstance(descriptor, dict):
            issues.append(f"embeddings[{i}] is not an object")
            continue
        if descriptor.get("included"):
            path = descriptor.get("path")
            if not path:
                issues.append(f"embeddings[{i}] is included but declares no sidecar path")
            elif path not in asset_paths or not pkg.container.has(path):
                issues.append(
                    f"embeddings[{i}] sidecar is not a declared, present asset: {path!r}"
                )
    return True, issues


def check_signed(pkg) -> tuple[bool, list[str]]:
    """Signed: at least one declared signature verifies over the manifest bytes
    (offline, fail-closed). The class is granted only when a signature actually
    verifies; signatures that are present but unverifiable (a bad signature, or the
    verifying extra not installed) leave the class ungranted with a warning."""
    signatures = pkg.manifest.raw.get("signatures")
    if not signatures:
        return False, []
    results = pkg.verify_signatures()
    if any(result.get("verified") for result in results):
        return True, []
    reasons = "; ".join(result.get("error") or "did not verify" for result in results)
    return True, [f"no signature verified: {reasons}"]


# Ordered list of (class-name, checker). package.validate() consults this after
# Core passes. Higher classes are independent capabilities over Core, not a stack.
CHECKERS = [
    ("sources", check_sources),
    ("shapes", check_shapes),
    ("embeddings", check_embeddings),
    ("signed", check_signed),
]
