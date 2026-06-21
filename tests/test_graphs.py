import pytest
from rdflib import Literal, URIRef

from ccx.container import Container
from ccx.errors import CCXSecurityError
from ccx.manifest import load_manifest
from ccx import graphs
from tests import fixtures


def _manifest_of(data: bytes):
    import json

    c = Container.open(data)
    return c, load_manifest(json.loads(c.read("manifest.json")))


def test_loads_default_graph_with_expected_triple():
    container, manifest = _manifest_of(fixtures.core_minimal())
    ds = graphs.load_dataset(container, manifest)
    alice = URIRef("urn:ccx:demo:alice")
    name = URIRef("https://schema.org/name")
    triples = list(ds.default_graph.triples((alice, name, None)))
    assert (alice, name, Literal("Alice Smith")) in [
        (s, p, o) for (s, p, o) in triples
    ]


def test_remote_context_is_rejected():
    container, manifest = _manifest_of(fixtures.remote_context())
    with pytest.raises(CCXSecurityError):
        graphs.load_dataset(container, manifest)


def test_no_network_blocks_connect():
    import socket

    with pytest.raises(CCXSecurityError):
        with graphs.no_network():
            socket.socket().connect(("example.com", 80))


def test_reject_remote_context_recurses_into_nested_nodes():
    from ccx.graphs import reject_remote_context

    doc = {
        "@context": {"x": "https://schema.org/x"},
        "@graph": [{"@context": "https://evil.example/c"}],
    }
    with pytest.raises(CCXSecurityError):
        reject_remote_context(doc)


def test_reject_remote_context_rejects_remote_import():
    from ccx.graphs import reject_remote_context

    doc = {"@context": {"@import": "https://evil.example/base.jsonld"}}
    with pytest.raises(CCXSecurityError):
        reject_remote_context(doc)


def test_no_network_reentrancy_raises_ccx_security_error():
    with pytest.raises(CCXSecurityError):
        with graphs.no_network():
            with graphs.no_network():
                pass


def test_app_namespace_graph_loads_as_named_graph():
    from rdflib import Literal, URIRef

    container, manifest = _manifest_of(fixtures.core_with_app_graph())
    ds = graphs.load_dataset(container, manifest)

    alice = URIRef("urn:ccx:demo:alice")
    schema_name = URIRef("https://schema.org/name")
    acme_note = URIRef("https://acme.example/ns#note")

    # The ccx default graph holds the knowledge triple.
    assert (alice, schema_name, Literal("Alice Smith")) in ds.default_graph

    # The app graph is loaded under its namespaced graph IRI, NOT the default graph.
    named = ds.graph(URIRef(graphs.graph_iri("acme", "notes")))
    assert (alice, acme_note, Literal("Reviewed by Acme")) in named
    assert (alice, acme_note, Literal("Reviewed by Acme")) not in ds.default_graph
