"""Load JSON-LD graph files into an rdflib Dataset, with no network access."""

from __future__ import annotations

import json
import socket
from contextlib import contextmanager

import rdflib

from .errors import CCXSecurityError, CCXValidationError


@contextmanager
def no_network():
    """Block all outbound socket connections for the duration of the block.

    Patches ``socket.socket.connect`` process-wide; it is NOT thread-safe or
    reentrant. Reading a CCX package is synchronous, so a single guard wraps the
    whole parse. The reentrancy guard raises if the patch is already active.
    """
    original = socket.socket.connect
    if getattr(original, "_ccx_blocked", False):
        raise CCXSecurityError("no_network() is not reentrant")

    def blocked(self, *args, **kwargs):
        raise CCXSecurityError("network access blocked while reading package")

    blocked._ccx_blocked = True
    socket.socket.connect = blocked
    try:
        yield
    finally:
        socket.socket.connect = original


def graph_iri(namespace: str, name: str) -> str:
    return f"https://w3id.org/ccx/graph/{namespace}/{name}"


def reject_remote_context(doc: object) -> None:
    """Raise CCXSecurityError if a JSON-LD doc references a remote context anywhere.

    Walks the whole structure: a remote ``@context`` (string or list element) or a
    remote JSON-LD 1.1 ``@import`` is rejected whether it sits at the top level,
    inside ``@graph``, or in a node-scoped context nested anywhere.
    """

    def is_remote(value: object) -> bool:
        return isinstance(value, str) and value.startswith(("http://", "https://"))

    if isinstance(doc, dict):
        ctx = doc.get("@context")
        candidates = ctx if isinstance(ctx, list) else [ctx]
        for candidate in candidates:
            if is_remote(candidate):
                raise CCXSecurityError(
                    f"remote @context not allowed: {candidate!r} (bundle it in the package)"
                )
        imported = doc.get("@import")
        if is_remote(imported):
            raise CCXSecurityError(
                f"remote @import not allowed: {imported!r} (bundle it in the package)"
            )
        for value in doc.values():
            reject_remote_context(value)
    elif isinstance(doc, list):
        for item in doc:
            reject_remote_context(item)


def is_default(entry) -> bool:
    return entry.role == "default" or entry.namespace == "ccx"


def load_dataset(container, manifest) -> rdflib.Dataset:
    """Assemble the package's graphs into an rdflib Dataset.

    The `knowledge` graph (role 'default' or namespace 'ccx') becomes the RDF
    default graph; every other declared graph becomes a named graph.
    """
    dataset = rdflib.Dataset()
    with no_network():
        for entry in manifest.graphs:
            text = container.read(entry.path).decode("utf-8")
            reject_remote_context(json.loads(text))
            target = (
                dataset.default_graph
                if is_default(entry)
                else dataset.graph(rdflib.URIRef(graph_iri(entry.namespace, entry.name)))
            )
            try:
                target.parse(data=text, format="json-ld")
            except CCXSecurityError:
                raise
            except Exception as exc:  # noqa: BLE001 - surface a uniform error
                raise CCXValidationError(
                    f"failed to parse graph {entry.path!r}: {exc}"
                ) from exc
    return dataset
