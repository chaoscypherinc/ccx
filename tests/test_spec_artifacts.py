"""Tests that the machine artifacts (bundled @context, fixtures) stay in sync
with the normative spec under spec/."""

from __future__ import annotations

import json
from pathlib import Path

import ccx
from ccx.context import default_context
from ccx.manifest import validate_manifest_data
from tests import fixtures

ROOT = Path(__file__).resolve().parent.parent


def test_context_defines_core_terms():
    ctx = default_context()["@context"]
    for term in ("ccx", "Relationship", "subject", "predicate", "object"):
        assert term in ctx, f"missing context term: {term}"


def test_spec_files_exist():
    spec = ROOT / "spec"
    for name in (
        "README",
        "ccx-3.0",
        "manifest",
        "knowledge",
        "vocabulary",
        "versioning",
        "conformance",
    ):
        assert (spec / f"{name}.md").is_file(), name


def test_valid_core_fixture_still_validates():
    assert ccx.open_package(fixtures.core_minimal()).validate().ok is True


def test_schema_accepts_full_vision_optionals():
    """The manifest schema explicitly accepts the higher-class optional fields."""
    manifest = {
        "ccx_version": "3.0",
        "name": "demo/people",
        "package_version": "1.0.0",
        "graphs": [
            {
                "namespace": "ccx",
                "role": "default",
                "name": "knowledge",
                "path": "knowledge.jsonld",
                "media_type": "application/ld+json",
                "sha256": "x",
                "sha512": "y",
                "license": "CC-BY-4.0",
            }
        ],
        "assets": [
            {
                "path": "assets/sha256/abc",
                "media_type": "application/pdf",
                "sha256": "x",
                "sha512": "y",
                "source_mode": "embedded",
                "license": "CC-BY-4.0",
            }
        ],
        "embeddings": [
            {
                "model": "text-embedding-3-small",
                "provider": "openai",
                "dimensions": 1536,
                "included": True,
                "path": "assets/sha256/vec",
            }
        ],
        "signatures": [{"path": "signatures/manifest.sig", "format": "sigstore"}],
    }
    validate_manifest_data(manifest)  # must not raise


HIGHER_CLASS_VALID = {
    "sources": fixtures.sources_minimal,
    "embeddings": fixtures.embeddings_minimal,
    "signed": fixtures.signed_minimal,
    "shapes": fixtures.shapes_minimal,
}


def test_higher_class_valid_fixtures_pass_core():
    for label, builder in HIGHER_CLASS_VALID.items():
        report = ccx.open_package(builder()).validate()
        assert report.ok is True, f"{label}: {report.errors}"


def test_sources_jsonl_parses_as_jsonl():
    pkg = ccx.open_package(fixtures.sources_minimal())
    raw = pkg.container.read("sources.jsonl").decode("utf-8")
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    assert len(records) == 2
    assert records[0]["@type"] == "Source"


def test_embeddings_descriptor_roundtrips():
    pkg = ccx.open_package(fixtures.embeddings_minimal())
    assert pkg.manifest.raw["embeddings"][0]["dimensions"] == 1536


def test_shapes_ttl_is_valid_turtle():
    import rdflib

    pkg = ccx.open_package(fixtures.shapes_minimal())
    graph = rdflib.Graph()
    graph.parse(data=pkg.container.read("shapes.ttl").decode("utf-8"), format="turtle")
    assert len(graph) > 0


def test_compressed_mimetype_is_rejected():
    report = ccx.open_package(fixtures.compressed_mimetype()).validate()
    assert report.ok is False
    assert any("STORED" in e or "stored" in e for e in report.errors)


def test_context_defines_all_spec_terms():
    """The bundled context MUST define every ccx: term the spec enumerates in
    spec/vocabulary.md (core edge terms + sources/citation terms + embedding terms)."""
    ctx = default_context()["@context"]
    expected = {
        "ccx",
        "Relationship",
        "subject",
        "predicate",
        "object",
        "Source",
        "Chunk",
        "Citation",
        "selector",
        "sourceMode",
        "extractedBy",
        "embeddingModel",
        "dimensions",
        "citation",
        "confidence",
        "extractionMethod",
    }
    missing = expected - set(ctx)
    assert not missing, f"context.jsonld missing terms: {sorted(missing)}"


def test_minimal_embedding_descriptor_is_schema_valid():
    """The embeddings descriptor requires only model + dimensions (A5 reconcile)."""
    from ccx.manifest import validate_manifest_data

    manifest = {
        "ccx_version": "3.0",
        "name": "demo/x",
        "package_version": "1.0.0",
        "graphs": [
            {
                "namespace": "ccx",
                "role": "default",
                "name": "knowledge",
                "path": "knowledge.jsonld",
                "media_type": "application/ld+json",
                "sha256": "x",
                "sha512": "y",
            }
        ],
        "embeddings": [{"model": "m", "dimensions": 8}],  # only model + dimensions
    }
    validate_manifest_data(manifest)  # must not raise
