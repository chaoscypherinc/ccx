import pytest

from ccx import open_package
from ccx.errors import CCXSecurityError, CCXValidationError
from ccx.writer import PackageBuilder


def _knowledge_doc():
    return {
        "@context": {
            "ccx": "https://w3id.org/ccx/",
            "schema": "https://schema.org/",
            "name": "schema:name",
            "Person": "schema:Person",
        },
        "@graph": [
            {"@id": "urn:ccx:demo:alice", "@type": "Person", "name": "Alice Smith"}
        ],
    }


def test_build_minimal_valid_package():
    b = PackageBuilder(name="demo/people", package_version="1.0.0", license="CC-BY-4.0")
    b.add_graph("ccx", "knowledge", _knowledge_doc(), role="default")
    data = b.build()
    pkg = open_package(data)
    report = pkg.validate()
    assert report.ok is True
    assert report.conformance_level == "core"
    assert pkg.manifest.name == "demo/people"


def test_named_graph_written_to_graphs_dir():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.add_graph("ccx", "knowledge", _knowledge_doc(), role="default")
    b.add_graph("acme", "notes", {"@context": {"acme": "https://acme.example/ns#"}, "@graph": []})
    pkg = open_package(b.build())
    paths = {g.path for g in pkg.manifest.graphs}
    assert "knowledge.jsonld" in paths
    assert "graphs/acme.notes.jsonld" in paths


def test_build_is_deterministic():
    def make():
        b = PackageBuilder(name="demo/people", package_version="1.0.0",
                           created_at="2026-06-16T00:00:00Z")
        b.add_graph("ccx", "knowledge", _knowledge_doc(), role="default")
        return b.build()
    assert make() == make()


def test_build_requires_a_graph():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    with pytest.raises(CCXValidationError):
        b.build()


def test_generator_defaults_and_created_at_optional():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.add_graph("ccx", "knowledge", _knowledge_doc(), role="default")
    pkg = open_package(b.build())
    assert pkg.manifest.generator.startswith("ccx-format@")
    assert pkg.manifest.created_at is None


def test_duplicate_graph_path_raises():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.add_graph("foo.bar", "baz", {"@graph": []})
    b.add_graph("foo", "bar.baz", {"@graph": []})  # collides → graphs/foo.bar.baz.jsonld
    with pytest.raises(CCXValidationError):
        b.build()


def test_invalid_role_raises():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    with pytest.raises(CCXValidationError):
        b.add_graph("ccx", "knowledge", _knowledge_doc(), role="primary")


def test_add_asset_content_addressed():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.add_graph("ccx", "knowledge", _knowledge_doc(), role="default")
    path = b.add_asset(b"\x89PNG\r\n\x1a\nhello", media_type="image/png")
    assert path.startswith("assets/sha256/")
    pkg = open_package(b.build())
    assert any(a.path == path for a in pkg.manifest.assets)
    assert pkg.asset_bytes(path) == b"\x89PNG\r\n\x1a\nhello"


def test_add_asset_explicit_path_and_dedup():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.add_graph("ccx", "knowledge", _knowledge_doc(), role="default")
    p1 = b.add_asset(b"same-bytes", media_type="text/plain", path="assets/a.txt")
    p2 = b.add_asset(b"same-bytes", media_type="text/plain", path="assets/a.txt")
    assert p1 == p2 == "assets/a.txt"
    pkg = open_package(b.build())
    assert sum(1 for a in pkg.manifest.assets if a.path == "assets/a.txt") == 1


def test_add_asset_conflicting_path_raises():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.add_asset(b"one", media_type="text/plain", path="assets/a.txt")
    with pytest.raises(CCXValidationError):
        b.add_asset(b"two", media_type="text/plain", path="assets/a.txt")


def test_add_graph_accepts_rdflib_graph():
    import rdflib
    from rdflib import Literal, URIRef

    g = rdflib.Graph()
    alice = URIRef("urn:ccx:demo:alice")
    g.add((alice, URIRef("https://schema.org/name"), Literal("Alice Smith")))

    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.add_graph("ccx", "knowledge", g, role="default")
    pkg = open_package(b.build())

    ds = pkg.dataset()
    assert (alice, URIRef("https://schema.org/name"), Literal("Alice Smith")) in ds.default_graph


def test_extend_context_merges_terms():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.extend_context({"acme": "https://acme.example/ns#"})
    b.add_graph("ccx", "knowledge", {"@graph": []}, role="default")  # no inline context
    pkg = open_package(b.build())
    assert pkg.context()["@context"]["acme"] == "https://acme.example/ns#"
    assert pkg.context()["@context"]["ccx"] == "https://w3id.org/ccx/"  # default kept


def test_extend_context_rejects_remote():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    with pytest.raises(CCXSecurityError):
        b.extend_context({"@import": "https://evil.example/ctx"})


def test_set_context_replaces():
    b = PackageBuilder(name="demo/people", package_version="1.0.0")
    b.set_context({"@context": {"ccx": "https://w3id.org/ccx/", "x": "ccx:x"}})
    b.add_graph("ccx", "knowledge", {"@graph": []}, role="default")
    pkg = open_package(b.build())
    assert pkg.context()["@context"]["x"] == "ccx:x"


def test_write_package_function(tmp_path):
    from ccx import write_package

    out = tmp_path / "p.ccx"
    write_package(
        str(out),
        name="demo/people",
        package_version="1.0.0",
        license="CC-BY-4.0",
        graphs=[("ccx", "knowledge", _knowledge_doc(), "default")],
        assets=[(b"\x89PNG\r\n\x1a\nx", "image/png", None)],
    )
    pkg = open_package(str(out))
    assert pkg.validate().ok is True
    assert len(pkg.manifest.assets) == 1


def test_ccx_namespace_reserved_for_knowledge():
    b = PackageBuilder(name="d/p", package_version="1.0.0")
    with pytest.raises(CCXValidationError):
        b.add_graph("ccx", "lenses", {"@graph": []})


def test_default_role_only_for_ccx_knowledge():
    b = PackageBuilder(name="d/p", package_version="1.0.0")
    with pytest.raises(CCXValidationError):
        b.add_graph("acme", "main", {"@graph": []}, role="default")


def test_graph_namespace_rejects_traversal():
    b = PackageBuilder(name="d/p", package_version="1.0.0")
    with pytest.raises(CCXValidationError):
        b.add_graph("../evil", "x", {"@graph": []})


def test_asset_path_collision_with_graph_raises():
    b = PackageBuilder(name="d/p", package_version="1.0.0")
    b.add_graph("ccx", "knowledge", _knowledge_doc(), role="default")
    b.add_asset(b"x", media_type="text/plain", path="knowledge.jsonld")
    with pytest.raises(CCXValidationError):
        b.build()


def test_set_context_requires_context_key():
    b = PackageBuilder(name="d/p", package_version="1.0.0")
    with pytest.raises(CCXValidationError):
        b.set_context({"ccx": "https://w3id.org/ccx/"})


def test_write_package_accepts_three_tuple_graph(tmp_path):
    from ccx import write_package

    out = tmp_path / "p.ccx"
    write_package(str(out), name="d/p", package_version="1.0.0",
                  graphs=[("ccx", "knowledge", _knowledge_doc())])
    assert open_package(str(out)).validate().ok is True
