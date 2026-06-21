"""Core + Sources conformance: reader enforcement + writer round-trip."""

from __future__ import annotations

import ccx
from tests import fixtures


def test_core_package_has_only_core_class():
    report = ccx.open_package(fixtures.core_minimal()).validate()
    assert report.ok
    assert report.classes == ("core",)


def test_sources_fixture_grants_sources_class():
    report = ccx.open_package(fixtures.sources_minimal()).validate()
    assert report.ok
    assert "core" in report.classes
    assert "sources" in report.classes


def test_sources_api_returns_records():
    pkg = ccx.open_package(fixtures.sources_minimal())
    records = pkg.sources()
    assert len(records) == 2
    assert records[0]["@type"] == "Source"


def test_core_package_sources_api_is_empty():
    assert ccx.open_package(fixtures.core_minimal()).sources() == []


def test_writer_add_source_round_trips_and_grants_class():
    builder = ccx.PackageBuilder(
        name="demo/people",
        package_version="1.0.0",
        license="CC-BY-4.0",
        base_iri="urn:ccx:demo:",
    )
    builder.add_graph("ccx", "knowledge", {"@graph": []}, role="default")
    builder.add_source(
        {
            "@id": "urn:ccx:demo:source/doc",
            "@type": "Source",
            "selector": {"type": "TextPositionSelector", "start": 0, "end": 5},
        },
        text=b"hello world",
        source_mode="derived-only",
    )
    data = builder.build()
    report = ccx.open_package(data).validate()
    assert report.ok
    assert "sources" in report.classes
    assert ccx.open_package(data).sources()[0]["@type"] == "Source"


def test_bad_offset_selector_is_core_ok_but_not_sources_conformant():
    builder = ccx.PackageBuilder(
        name="demo/people",
        package_version="1.0.0",
        license="CC-BY-4.0",
        base_iri="urn:ccx:demo:",
    )
    builder.add_graph("ccx", "knowledge", {"@graph": []}, role="default")
    builder.add_source(
        {
            "@id": "urn:ccx:demo:source/doc",
            "@type": "Source",
            "selector": {"type": "TextPositionSelector", "start": 0, "end": 999},
        },
        text=b"short",
        source_mode="derived-only",
    )
    data = builder.build()  # core-valid, so build() self-validation passes
    report = ccx.open_package(data).validate()
    assert report.ok  # Core integrity is intact
    assert "sources" not in report.classes  # but the Sources class is not granted
    assert any("exceeds" in w for w in report.warnings)


def test_inline_content_chunk_grants_sources_class():
    report = ccx.open_package(fixtures.sources_inline_chunk()).validate()
    assert report.ok
    assert "sources" in report.classes


def test_inline_content_chunk_is_readable():
    pkg = ccx.open_package(fixtures.sources_inline_chunk())
    chunk = [r for r in pkg.sources() if r.get("@type") == "ccx:Chunk"][0]
    assert chunk["content"] == "Alice Smith works for Acme Corporation."
    assert "ccx:selector" not in chunk  # the inline form carries no selector


def test_source_carries_chunking_provenance():
    pkg = ccx.open_package(fixtures.sources_inline_chunk())
    src = [r for r in pkg.sources() if r.get("@type") == "ccx:Source"][0]
    assert src["chunking"]["strategy"] == "recursive_character"
    assert src["chunking"]["overlap"] == 64


def test_sources_only_package_is_conformant():
    pkg = ccx.open_package(fixtures.sources_only())
    report = pkg.validate()
    assert report.ok
    assert "sources" in report.classes
    know = [g for g in pkg.graph_documents() if g.name == "knowledge"][0]
    assert know.doc.get("@graph") == []  # à-la-carte: empty knowledge graph
