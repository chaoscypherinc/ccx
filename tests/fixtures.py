"""In-memory .ccx fixture builders for tests and the shipped conformance suite."""

from __future__ import annotations

import io
import json
import zipfile

from ccx.checksums import compute, sha256_hex
from ccx.constants import CCX_VERSION, CONTEXT_PATH, MANIFEST_PATH, MEDIA_TYPE_JSONLD, MIMETYPE, MIMETYPE_PATH

CONTEXT = {
    "@context": {
        "ccx": "https://w3id.org/ccx/",
        "schema": "https://schema.org/",
        "name": "schema:name",
        "worksFor": "schema:worksFor",
        "Person": "schema:Person",
        "Organization": "schema:Organization",
    }
}

KNOWLEDGE = {
    "@context": CONTEXT["@context"],
    "@graph": [
        {
            "@id": "urn:ccx:demo:alice",
            "@type": "Person",
            "name": "Alice Smith",
            "worksFor": {"@id": "urn:ccx:demo:acme"},
        },
        {
            "@id": "urn:ccx:demo:acme",
            "@type": "Organization",
            "name": "Acme Corporation",
        },
    ],
}

APP_GRAPH = {
    "@context": {"acme": "https://acme.example/ns#", "note": "acme:note"},
    "@graph": [
        {"@id": "urn:ccx:demo:alice", "note": "Reviewed by Acme"},
    ],
}


def _pack(entries: list[tuple[str, bytes]]) -> bytes:
    """Write (arcname, bytes) entries in order. `mimetype` is stored uncompressed."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries:
            compress = (
                zipfile.ZIP_STORED if name == MIMETYPE_PATH else zipfile.ZIP_DEFLATED
            )
            zf.writestr(zipfile.ZipInfo(name), data, compress_type=compress)
    return buf.getvalue()


def _manifest(knowledge_bytes: bytes, **overrides) -> dict:
    s256, s512 = compute(knowledge_bytes)
    base = {
        "ccx_version": CCX_VERSION,
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
                "media_type": MEDIA_TYPE_JSONLD,
                "sha256": s256,
                "sha512": s512,
            }
        ],
        "assets": [],
    }
    base.update(overrides)
    return base


def core_minimal() -> bytes:
    """A valid Core package."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(_manifest(know), indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def core_with_app_graph() -> bytes:
    """Valid package: the ccx default `knowledge` graph PLUS an `acme` named graph
    that annotates a default-graph entity by @id."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    app = json.dumps(APP_GRAPH).encode("utf-8")
    s256, s512 = compute(know)
    a256, a512 = compute(app)
    manifest_dict = {
        "ccx_version": CCX_VERSION,
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
                "media_type": MEDIA_TYPE_JSONLD,
                "sha256": s256,
                "sha512": s512,
            },
            {
                "namespace": "acme",
                "name": "notes",
                "path": "graphs/acme.notes.jsonld",
                "media_type": MEDIA_TYPE_JSONLD,
                "sha256": a256,
                "sha512": a512,
            },
        ],
        "assets": [],
    }
    manifest = json.dumps(manifest_dict, indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            ("graphs/acme.notes.jsonld", app),
            (MANIFEST_PATH, manifest),
        ]
    )


def bad_checksum() -> bytes:
    """Valid structure, but knowledge bytes do not match the manifest hash."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    original = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(_manifest(original), indent=2).encode("utf-8")
    tampered = original.replace(b"Alice Smith", b"TAMPERED")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", tampered),
            (MANIFEST_PATH, manifest),
        ]
    )


def missing_mimetype() -> bytes:
    """No mimetype entry at all."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(_manifest(know), indent=2).encode("utf-8")
    return _pack(
        [
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def compressed_mimetype() -> bytes:
    """mimetype present and first, but DEFLATED rather than STORED (must be rejected)."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(_manifest(know), indent=2).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            zipfile.ZipInfo(MIMETYPE_PATH),
            MIMETYPE.encode("utf-8"),
            compress_type=zipfile.ZIP_DEFLATED,  # violates the STORED requirement
        )
        zf.writestr(zipfile.ZipInfo(CONTEXT_PATH), ctx, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr(zipfile.ZipInfo("knowledge.jsonld"), know, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr(zipfile.ZipInfo(MANIFEST_PATH), manifest, compress_type=zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def missing_manifest() -> bytes:
    """No manifest.json."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
        ]
    )


def invalid_manifest() -> bytes:
    """manifest.json missing the required `name` field."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    bad = _manifest(know)
    del bad["name"]
    manifest = json.dumps(bad, indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def remote_context() -> bytes:
    """Checksums are correct, but knowledge.jsonld points @context at a remote URL."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    remote = {"@context": "https://evil.example/ctx.jsonld", "@graph": []}
    know = json.dumps(remote).encode("utf-8")
    manifest = json.dumps(_manifest(know), indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def path_traversal() -> bytes:
    """Contains an entry that escapes the archive root."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(_manifest(know), indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            ("../evil.txt", b"escape"),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def malformed_manifest() -> bytes:
    """manifest.json is not valid JSON."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, b"{ this is not valid json"),
        ]
    )


def corrupt_context() -> bytes:
    """context.jsonld is not valid JSON (manifest + knowledge are fine)."""
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(_manifest(know), indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, b"{ not valid json"),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def valid_without_license() -> bytes:
    """A valid Core package with no license (validates OK, but warns)."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest_dict = _manifest(know)
    del manifest_dict["license"]
    manifest = json.dumps(manifest_dict, indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def remote_context_in_context_file() -> bytes:
    """context.jsonld itself references a remote @context (must be rejected)."""
    bad_ctx = json.dumps({"@context": "https://evil.example/ctx.jsonld"}).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(_manifest(know), indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, bad_ctx),
            ("knowledge.jsonld", know),
            (MANIFEST_PATH, manifest),
        ]
    )


def core_with_asset() -> bytes:
    """Valid package: the ccx default graph plus one declared asset."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    asset = b"\x89PNG\r\n\x1a\n-demo-bytes"
    s256, s512 = compute(know)
    a256, a512 = compute(asset)
    manifest_dict = {
        "ccx_version": CCX_VERSION,
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
                "media_type": MEDIA_TYPE_JSONLD,
                "sha256": s256,
                "sha512": s512,
            }
        ],
        "assets": [
            {
                "path": "assets/preview.png",
                "media_type": "image/png",
                "sha256": a256,
                "sha512": a512,
            }
        ],
    }
    manifest = json.dumps(manifest_dict, indent=2).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            ("assets/preview.png", asset),
            (MANIFEST_PATH, manifest),
        ]
    )


def _core_graphs(know_bytes: bytes) -> list[dict]:
    """The single ccx/knowledge default-graph entry, checksummed."""
    s256, s512 = compute(know_bytes)
    return [
        {
            "namespace": "ccx",
            "role": "default",
            "name": "knowledge",
            "path": "knowledge.jsonld",
            "media_type": MEDIA_TYPE_JSONLD,
            "sha256": s256,
            "sha512": s512,
        }
    ]


def _base_manifest(know_bytes: bytes, **extra) -> dict:
    """A Core manifest skeleton (ccx/knowledge graph, empty assets) plus `extra`."""
    m = {
        "ccx_version": CCX_VERSION,
        "name": "demo/people",
        "package_version": "1.0.0",
        "license": "CC-BY-4.0",
        "base_iri": "urn:ccx:demo:",
        "graphs": _core_graphs(know_bytes),
        "assets": [],
    }
    m.update(extra)
    return m


def sources_minimal() -> bytes:
    """Valid Core + Sources package: a content-addressed extracted-text asset, a
    `sources.jsonl` index (a Source record + a Chunk record with an offset
    selector), and the text asset declared with `source_mode: derived-only`."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    text = b"Alice Smith works for Acme Corporation."
    text_path = f"assets/sha256/{sha256_hex(text)}"
    sources = (
        json.dumps(
            {
                "@id": "urn:ccx:demo:source/hr-doc",
                "@type": "Source",
                "sourceMode": "derived-only",
                "extractedBy": "demo-parser@1.0",
                "text": text_path,
            }
        )
        + "\n"
        + json.dumps(
            {
                "@id": "urn:ccx:demo:source/hr-doc#chunk-1",
                "@type": "Chunk",
                "selector": {"type": "TextPositionSelector", "start": 0, "end": 11},
            }
        )
        + "\n"
    ).encode("utf-8")
    t256, t512 = compute(text)
    s256, s512 = compute(sources)
    manifest = json.dumps(
        _base_manifest(
            know,
            assets=[
                {
                    "path": text_path,
                    "media_type": "text/plain",
                    "sha256": t256,
                    "sha512": t512,
                    "source_mode": "derived-only",
                },
                {
                    "path": "sources.jsonl",
                    "media_type": "application/x-ndjson",
                    "sha256": s256,
                    "sha512": s512,
                },
            ],
        ),
        indent=2,
    ).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (text_path, text),
            ("sources.jsonl", sources),
            (MANIFEST_PATH, manifest),
        ]
    )


def sources_inline_chunk() -> bytes:
    """Valid Core + Sources package whose chunk carries INLINE content (the
    graduated fallback) — no text asset, no selector. The source also carries
    chunking provenance."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    sources = (
        json.dumps(
            {
                "@id": "urn:ccx:demo:source/doc",
                "@type": "ccx:Source",
                "title": "Doc",
                "extractedBy": "demo-parser/1.0",
                "chunking": {
                    "strategy": "recursive_character",
                    "target_size": 512,
                    "overlap": 64,
                    "min_size": 64,
                    "max_size": 1024,
                    "separators": ["\n\n", "\n", ". "],
                    "normalize": True,
                },
            }
        )
        + "\n"
        + json.dumps(
            {
                "@id": "urn:ccx:demo:source/doc#chunk-1",
                "@type": "ccx:Chunk",
                "source": {"@id": "urn:ccx:demo:source/doc"},
                "content": "Alice Smith works for Acme Corporation.",
            }
        )
        + "\n"
    ).encode("utf-8")
    s256, s512 = compute(sources)
    manifest = json.dumps(
        _base_manifest(
            know,
            assets=[
                {
                    "path": "sources.jsonl",
                    "media_type": "application/x-ndjson",
                    "sha256": s256,
                    "sha512": s512,
                    "source_mode": "derived-only",
                }
            ],
        ),
        indent=2,
    ).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            ("sources.jsonl", sources),
            (MANIFEST_PATH, manifest),
        ]
    )


def sources_only() -> bytes:
    """À-la-carte sources-only package: an EMPTY ccx/knowledge default graph plus
    sources.jsonl (no knowledge entities)."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    empty_know = json.dumps({"@context": CONTEXT["@context"], "@graph": []}).encode("utf-8")
    sources = (
        json.dumps(
            {
                "@id": "urn:ccx:demo:source/doc",
                "@type": "ccx:Source",
                "title": "Doc",
                "extractedBy": "demo-parser/1.0",
            }
        )
        + "\n"
    ).encode("utf-8")
    s256, s512 = compute(sources)
    manifest = json.dumps(
        _base_manifest(
            empty_know,
            assets=[
                {
                    "path": "sources.jsonl",
                    "media_type": "application/x-ndjson",
                    "sha256": s256,
                    "sha512": s512,
                    "source_mode": "derived-only",
                }
            ],
        ),
        indent=2,
    ).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", empty_know),
            ("sources.jsonl", sources),
            (MANIFEST_PATH, manifest),
        ]
    )


def embeddings_minimal() -> bytes:
    """Valid Embeddings package: a manifest embedding descriptor (`included`) plus a
    content-addressed binary vector sidecar."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    sidecar = b"PAR1-demo-vector-sidecar-bytes"  # stand-in for a Parquet sidecar
    sidecar_path = f"assets/sha256/{sha256_hex(sidecar)}"
    v256, v512 = compute(sidecar)
    manifest = json.dumps(
        _base_manifest(
            know,
            assets=[
                {
                    "path": sidecar_path,
                    "media_type": "application/vnd.apache.parquet",
                    "sha256": v256,
                    "sha512": v512,
                }
            ],
            embeddings=[
                {
                    "model": "text-embedding-3-small",
                    "provider": "openai",
                    "dimensions": 1536,
                    "included": True,
                    "path": sidecar_path,
                    "coverage": "entities",
                }
            ],
        ),
        indent=2,
    ).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            (sidecar_path, sidecar),
            (MANIFEST_PATH, manifest),
        ]
    )


# Fixed test key so the emitted Signed fixture is reproducible (Ed25519 is deterministic).
_SIGNED_FIXTURE_KEY = bytes(range(32))


def signed_minimal() -> bytes:
    """Valid Signed package: a real ed25519 detached signature over the manifest
    bytes, verifiable offline. Uses a fixed test key so the emitted fixture is
    byte-reproducible. The signature file is NOT a checksummed asset (the manifest
    is the signed payload — see trust.md §4.3)."""
    from ccx import signing

    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    manifest = json.dumps(
        _base_manifest(
            know,
            signatures=[
                {
                    "path": "signatures/manifest.sig",
                    "format": "ed25519",
                    "public_key": signing.public_key_b64(_SIGNED_FIXTURE_KEY),
                }
            ],
        ),
        indent=2,
    ).encode("utf-8")
    sig = signing.sign_ed25519(manifest, _SIGNED_FIXTURE_KEY)
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            ("signatures/manifest.sig", sig),
            (MANIFEST_PATH, manifest),
        ]
    )


def shapes_minimal() -> bytes:
    """Valid Shapes package: a `shapes.ttl` SHACL node shape declared + checksummed."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    shapes = (
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix schema: <https://schema.org/> .\n"
        "@prefix ccx: <https://w3id.org/ccx/> .\n"
        "ccx:PersonShape a sh:NodeShape ;\n"
        "    sh:targetClass schema:Person ;\n"
        "    sh:property [ sh:path schema:name ; sh:minCount 1 ] .\n"
    ).encode("utf-8")
    h256, h512 = compute(shapes)
    manifest = json.dumps(
        _base_manifest(
            know,
            assets=[
                {
                    "path": "shapes.ttl",
                    "media_type": "text/turtle",
                    "sha256": h256,
                    "sha512": h512,
                }
            ],
        ),
        indent=2,
    ).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            ("shapes.ttl", shapes),
            (MANIFEST_PATH, manifest),
        ]
    )


def signed_missing_sig() -> bytes:
    """Invalid: the manifest declares a `signatures/manifest.sig` asset that is NOT
    present in the archive — rejected by the Core declared-path-exists rule."""
    ctx = json.dumps(CONTEXT).encode("utf-8")
    know = json.dumps(KNOWLEDGE).encode("utf-8")
    sig = b"PLACEHOLDER-SIGNATURE"
    g256, g512 = compute(sig)  # checksum of bytes that are NOT shipped
    manifest = json.dumps(
        _base_manifest(
            know,
            assets=[
                {
                    "path": "signatures/manifest.sig",
                    "media_type": "application/octet-stream",
                    "sha256": g256,
                    "sha512": g512,
                }
            ],
            signatures=[{"path": "signatures/manifest.sig", "format": "sigstore"}],
        ),
        indent=2,
    ).encode("utf-8")
    return _pack(
        [
            (MIMETYPE_PATH, MIMETYPE.encode("utf-8")),
            (CONTEXT_PATH, ctx),
            ("knowledge.jsonld", know),
            # signatures/manifest.sig intentionally omitted
            (MANIFEST_PATH, manifest),
        ]
    )


# Registry of invalid-package builders, keyed by conformance-suite filename stem.
# Single source of truth consumed by scripts/emit_conformance.py and the tests so
# the set never drifts across files.
INVALID_BUILDERS = {
    "bad-checksum": bad_checksum,
    "signed-missing-sig": signed_missing_sig,
    "missing-mimetype": missing_mimetype,
    "compressed-mimetype": compressed_mimetype,
    "missing-manifest": missing_manifest,
    "invalid-manifest": invalid_manifest,
    "malformed-manifest": malformed_manifest,
    "remote-context": remote_context,
    "remote-context-file": remote_context_in_context_file,
    "corrupt-context": corrupt_context,
    "path-traversal": path_traversal,
}
