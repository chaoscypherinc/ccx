"""Shared constants for the CCX 3.0 format."""

from __future__ import annotations

MIMETYPE = "application/vnd.ccx+zip"
CCX_VERSION = "3.0"

MIMETYPE_PATH = "mimetype"
MANIFEST_PATH = "manifest.json"
CONTEXT_PATH = "context.jsonld"
SOURCES_PATH = "sources.jsonl"
SHAPES_PATH = "shapes.ttl"
SIGNATURE_PATH = "signatures/manifest.sig"  # default ed25519 detached signature
SIGSTORE_PATH = "signatures/manifest.sigstore"  # default Sigstore bundle

MEDIA_TYPE_JSONLD = "application/ld+json"
MEDIA_TYPE_JSONL = "application/x-ndjson"
MEDIA_TYPE_TURTLE = "text/turtle"

# Per-source media modes (manifest asset `source_mode`).
SOURCE_MODES = ("embedded", "referenced", "derived-only")

# Hardening limits (defense against zip bombs / pathological archives).
MAX_ENTRIES = 100_000
MAX_ENTRY_UNCOMPRESSED = 512 * 1024 * 1024  # 512 MiB per entry
MAX_TOTAL_UNCOMPRESSED = 2 * 1024 * 1024 * 1024  # 2 GiB total
