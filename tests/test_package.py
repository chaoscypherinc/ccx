import pytest

from ccx.errors import CCXValidationError
from ccx.package import CCXPackage, ValidationReport, open_package
from tests import fixtures


def test_open_valid_package():
    pkg = open_package(fixtures.core_minimal())
    assert isinstance(pkg, CCXPackage)
    assert pkg.manifest.name == "demo/people"
    assert pkg.context()["@context"]["ccx"] == "https://w3id.org/ccx/"


def test_validate_core_ok():
    report = open_package(fixtures.core_minimal()).validate()
    assert isinstance(report, ValidationReport)
    assert report.ok is True
    assert report.errors == []
    assert report.conformance_level == "core"


def test_validate_detects_checksum_mismatch():
    report = open_package(fixtures.bad_checksum()).validate()
    assert report.ok is False
    assert any("checksum" in e for e in report.errors)


def test_validate_detects_missing_mimetype():
    report = open_package(fixtures.missing_mimetype()).validate()
    assert report.ok is False
    assert any("mimetype" in e or "entry" in e for e in report.errors)


def test_open_missing_manifest_raises():
    with pytest.raises(CCXValidationError):
        open_package(fixtures.missing_manifest())


def test_open_invalid_manifest_raises():
    with pytest.raises(CCXValidationError):
        open_package(fixtures.invalid_manifest())


def test_dataset_is_lazy_and_cached():
    pkg = open_package(fixtures.core_minimal())
    ds1 = pkg.dataset()
    ds2 = pkg.dataset()
    assert ds1 is ds2


def test_open_malformed_manifest_raises():
    with pytest.raises(CCXValidationError):
        open_package(fixtures.malformed_manifest())


def test_validate_detects_malformed_context():
    report = open_package(fixtures.corrupt_context()).validate()
    assert report.ok is False
    assert any("context" in e for e in report.errors)


def test_context_on_malformed_raises():
    pkg = open_package(fixtures.corrupt_context())
    with pytest.raises(CCXValidationError):
        pkg.context()


def test_app_graph_package_validates_core():
    report = open_package(fixtures.core_with_app_graph()).validate()
    assert report.ok is True
    assert report.conformance_level == "core"
