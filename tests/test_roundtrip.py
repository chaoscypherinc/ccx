from rdflib import Literal, URIRef

from ccx import open_package
from ccx.writer import PackageBuilder
from tests import fixtures


def _seed_bytes():
    b = PackageBuilder(name="demo/people", package_version="1.0.0", license="CC-BY-4.0",
                       base_iri="urn:ccx:demo:", created_at="2026-06-16T00:00:00Z")
    b.add_graph("ccx", "knowledge",
                {"@context": {"ccx": "https://w3id.org/ccx/", "schema": "https://schema.org/",
                              "name": "schema:name", "Person": "schema:Person"},
                 "@graph": [{"@id": "urn:ccx:demo:alice", "@type": "Person", "name": "Alice Smith"}]},
                role="default")
    b.add_graph("acme", "notes",
                {"@context": {"acme": "https://acme.example/ns#", "note": "acme:note"},
                 "@graph": [{"@id": "urn:ccx:demo:alice", "note": "hi"}]})
    b.add_asset(b"\x89PNG\r\n\x1a\nx", media_type="image/png", path="assets/p.png")
    return b.build()


def test_from_package_no_change_is_byte_identical():
    original = _seed_bytes()
    pkg = open_package(original)
    rebuilt = PackageBuilder.from_package(pkg).build()
    assert rebuilt == original


def test_from_package_edit_then_rewrite():
    pkg = open_package(_seed_bytes())
    b = PackageBuilder.from_package(pkg).with_version("1.1.0")
    b.add_graph("acme", "review", {"@context": {"acme": "https://acme.example/ns#"}, "@graph": []})
    pkg2 = open_package(b.build())
    assert pkg2.validate().ok is True
    assert pkg2.manifest.package_version == "1.1.0"
    paths = {g.path for g in pkg2.manifest.graphs}
    assert {"knowledge.jsonld", "graphs/acme.notes.jsonld", "graphs/acme.review.jsonld"} <= paths


def _seed_with_metadata():
    b = PackageBuilder(
        name="demo/people", package_version="1.0.0", license="CC-BY-4.0",
        base_iri="urn:ccx:demo:", created_at="2026-06-16T00:00:00Z",
        title="T", description="D", author="Acme",
        tags=["a", "b"], derived_from={"up/x": "0.1.0"}, dependencies={"dep/y": "2.0.0"},
    )
    b.add_graph("ccx", "knowledge",
                {"@context": {"ccx": "https://w3id.org/ccx/"}, "@graph": []}, role="default")
    return b.build()


def test_from_package_full_metadata_byte_identical():
    original = _seed_with_metadata()
    rebuilt = PackageBuilder.from_package(open_package(original)).build()
    assert rebuilt == original


def test_from_package_extend_context_does_not_mutate_source():
    pkg = open_package(_seed_bytes())
    before = dict(pkg.context()["@context"])
    builder = PackageBuilder.from_package(pkg)
    builder.extend_context({"newterm": "https://example.com/new#"})
    after = pkg.context()["@context"]
    assert "newterm" not in after
    assert after == before


def test_round_trip_preserves_named_graph_and_asset():
    pkg = open_package(_seed_bytes())
    ds = pkg.dataset()
    alice = URIRef("urn:ccx:demo:alice")
    assert (alice, URIRef("https://schema.org/name"), Literal("Alice Smith")) in ds.default_graph
    import ccx.graphs as g
    named = ds.graph(URIRef(g.graph_iri("acme", "notes")))
    assert (alice, URIRef("https://acme.example/ns#note"), Literal("hi")) in named
    assert pkg.asset_bytes("assets/p.png").startswith(b"\x89PNG")


def test_conformance_valid_fixtures_rebuild_via_writer():
    from ccx.writer import PackageBuilder

    pkg = open_package(fixtures.core_with_app_graph())
    rebuilt = PackageBuilder.from_package(pkg).build()
    assert open_package(rebuilt).validate().ok is True
