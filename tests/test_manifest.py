import pytest

from ccx import manifest as m
from ccx.errors import CCXValidationError

VALID = {
    "ccx_version": "3.0",
    "name": "demo/people",
    "package_version": "1.0.0",
    "license": "CC-BY-4.0",
    "base_iri": "urn:ccx:demo:",
    "graphs": [
        {
            "namespace": "ccx",
            "role": "default",
            "name": "knowledge",
            "path": "knowledge.jsonld",
            "media_type": "application/ld+json",
            "sha256": "aaa",
            "sha512": "bbb",
        }
    ],
}


def test_load_valid_manifest():
    parsed = m.load_manifest(VALID)
    assert parsed.name == "demo/people"
    assert parsed.ccx_version == "3.0"
    assert len(parsed.graphs) == 1
    g = parsed.graphs[0]
    assert g.namespace == "ccx"
    assert g.role == "default"
    assert g.path == "knowledge.jsonld"
    assert parsed.assets == ()


def test_missing_required_field_rejected():
    bad = {k: v for k, v in VALID.items() if k != "name"}
    with pytest.raises(CCXValidationError):
        m.load_manifest(bad)


def test_empty_graphs_rejected():
    bad = dict(VALID, graphs=[])
    with pytest.raises(CCXValidationError):
        m.load_manifest(bad)


def test_unknown_top_level_field_allowed_for_forward_compat():
    ok = dict(VALID, future_field={"anything": True})
    parsed = m.load_manifest(ok)
    assert parsed.raw["future_field"] == {"anything": True}


def test_role_enum_rejects_unknown_value():
    bad = dict(VALID)
    bad["graphs"] = [dict(VALID["graphs"][0], role="primary")]
    with pytest.raises(CCXValidationError):
        m.load_manifest(bad)


def test_assets_are_loaded():
    with_assets = dict(VALID)
    with_assets["assets"] = [
        {
            "path": "assets/sha256/abc",
            "media_type": "application/pdf",
            "sha256": "aaa",
            "sha512": "bbb",
        }
    ]
    parsed = m.load_manifest(with_assets)
    assert len(parsed.assets) == 1
    assert parsed.assets[0].path == "assets/sha256/abc"
    assert parsed.assets[0].media_type == "application/pdf"
