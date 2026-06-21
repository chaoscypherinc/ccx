import pytest

from ccx import open_package
from ccx.errors import CCXValidationError
from tests import fixtures


def test_graph_documents_returns_docs():
    pkg = open_package(fixtures.core_with_app_graph())
    docs = pkg.graph_documents()
    by_ns = {(d.namespace, d.name): d for d in docs}
    assert ("ccx", "knowledge") in by_ns
    assert ("acme", "notes") in by_ns
    knowledge = by_ns[("ccx", "knowledge")]
    assert knowledge.role == "default"
    assert knowledge.path == "knowledge.jsonld"
    assert "@graph" in knowledge.doc
    acme = by_ns[("acme", "notes")]
    assert acme.path == "graphs/acme.notes.jsonld"


def test_asset_bytes_reads_declared_asset():
    pkg = open_package(fixtures.core_with_asset())
    data = pkg.asset_bytes("assets/preview.png")
    assert data.startswith(b"\x89PNG")


def test_asset_bytes_unknown_path_raises():
    pkg = open_package(fixtures.core_minimal())
    with pytest.raises(CCXValidationError):
        pkg.asset_bytes("assets/missing.png")
