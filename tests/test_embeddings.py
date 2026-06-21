"""Embeddings conformance class: reader enforcement + writer round-trip.

Detecting the class needs no extra; reading vector sidecars needs the `embeddings`
extra (pyarrow).
"""

from __future__ import annotations

import pytest

import ccx
from tests import fixtures


def _builder():
    builder = ccx.PackageBuilder(
        name="demo/people",
        package_version="1.0.0",
        license="CC-BY-4.0",
        base_iri="urn:ccx:demo:",
    )
    builder.add_graph("ccx", "knowledge", {"@graph": []}, role="default")
    return builder


def test_embeddings_fixture_grants_class():
    report = ccx.open_package(fixtures.embeddings_minimal()).validate()
    assert report.ok
    assert "embeddings" in report.classes


def test_embeddings_api_returns_descriptors():
    descriptors = ccx.open_package(fixtures.embeddings_minimal()).embeddings()
    assert descriptors[0]["dimensions"] == 1536


def test_core_package_has_no_embeddings_class():
    report = ccx.open_package(fixtures.core_minimal()).validate()
    assert "embeddings" not in report.classes
    assert ccx.open_package(fixtures.core_minimal()).embeddings() == []


def test_writer_add_embeddings_with_sidecar_round_trips():
    data = (
        _builder()
        .add_embeddings(
            {"model": "demo-model", "provider": "demo", "dimensions": 8, "coverage": "entities"},
            sidecar=b"PAR1-demo-vectors",
        )
        .build()
    )
    report = ccx.open_package(data).validate()
    assert report.ok
    assert "embeddings" in report.classes
    assert ccx.open_package(data).embeddings()[0]["included"] is True


def test_provenance_only_descriptor_is_conformant():
    data = (
        _builder()
        .add_embeddings({"model": "demo-model", "dimensions": 8, "included": False})
        .build()
    )
    report = ccx.open_package(data).validate()
    assert report.ok
    assert "embeddings" in report.classes


def test_included_without_present_sidecar_is_not_conformant():
    data = (
        _builder()
        .add_embeddings(
            {"model": "demo-model", "dimensions": 8, "included": True, "path": "assets/sha256/bogus"}
        )
        .build()
    )
    report = ccx.open_package(data).validate()
    assert report.ok  # Core doesn't check the embeddings path (it isn't a declared asset)
    assert "embeddings" not in report.classes
    assert any("sidecar" in w for w in report.warnings)


def test_read_embeddings_requires_extra_or_raises_on_bad_parquet():
    pkg = ccx.open_package(fixtures.embeddings_minimal())
    descriptor = pkg.embeddings()[0]
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        with pytest.raises(ccx.CCXValidationError):
            pkg.read_embeddings(descriptor)
    else:
        # The fixture sidecar is placeholder bytes, not real Parquet, so it raises.
        with pytest.raises(Exception):
            pkg.read_embeddings(descriptor)
