"""Shapes conformance class: reader enforcement (rdflib-only) + writer round-trip.

Detecting the class needs no extra; SHACL data-validation needs the `shapes` extra.
"""

from __future__ import annotations

import pytest

import ccx
from tests import fixtures

_VALID_SHAPES = (
    b"@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
    b"@prefix schema: <https://schema.org/> .\n"
    b"<https://w3id.org/ccx/PersonShape> a sh:NodeShape ;\n"
    b"    sh:targetClass schema:Person ;\n"
    b"    sh:property [ sh:path schema:name ; sh:minCount 1 ] .\n"
)


def _builder():
    builder = ccx.PackageBuilder(
        name="demo/people",
        package_version="1.0.0",
        license="CC-BY-4.0",
        base_iri="urn:ccx:demo:",
    )
    builder.add_graph("ccx", "knowledge", {"@graph": []}, role="default")
    return builder


def test_shapes_fixture_grants_shapes_class():
    report = ccx.open_package(fixtures.shapes_minimal()).validate()
    assert report.ok
    assert "shapes" in report.classes


def test_shapes_api_returns_turtle():
    text = ccx.open_package(fixtures.shapes_minimal()).shapes()
    assert text is not None and "NodeShape" in text


def test_core_package_has_no_shapes_class():
    report = ccx.open_package(fixtures.core_minimal()).validate()
    assert "shapes" not in report.classes
    assert ccx.open_package(fixtures.core_minimal()).shapes() is None


def test_writer_add_shapes_round_trips_and_grants_class():
    data = _builder().add_shapes(_VALID_SHAPES).build()
    report = ccx.open_package(data).validate()
    assert report.ok
    assert "shapes" in report.classes


def test_invalid_turtle_is_core_ok_but_not_shapes_conformant():
    data = _builder().add_shapes(b"this is not valid turtle {{{").build()
    report = ccx.open_package(data).validate()
    assert report.ok  # shapes is an extension — malformed shapes don't break Core
    assert "shapes" not in report.classes
    assert any("Turtle" in w for w in report.warnings)


def test_turtle_without_a_shape_is_not_shapes_conformant():
    # Valid Turtle, but no sh:NodeShape / sh:PropertyShape.
    ttl = b"@prefix ex: <https://example.org/> .\nex:a ex:b ex:c .\n"
    data = _builder().add_shapes(ttl).build()
    report = ccx.open_package(data).validate()
    assert report.ok
    assert "shapes" not in report.classes
    assert any("NodeShape" in w for w in report.warnings)


def test_shacl_validate_requires_extra_or_runs():
    pkg = ccx.open_package(fixtures.shapes_minimal())
    try:
        import pyshacl  # noqa: F401
    except ImportError:
        with pytest.raises(ccx.CCXValidationError):
            pkg.shacl_validate()
    else:
        conforms, report_text = pkg.shacl_validate()
        assert isinstance(conforms, bool)
        assert isinstance(report_text, str)
