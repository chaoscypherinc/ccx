"""CCX (Chaos Cypher eXchange) — reference reader + writer for the open, portable
knowledge-graph package format. See https://github.com/chaoscypherinc/ccx."""

from __future__ import annotations

from .errors import (
    CCXError,
    CCXIntegrityError,
    CCXSecurityError,
    CCXValidationError,
)
from .manifest import AssetEntry, GraphEntry, Manifest, load_manifest
from .package import CCXPackage, ValidationReport, open_package
from .signing import generate_ed25519_keypair
from .writer import PackageBuilder, write_package

__version__ = "0.1.1"

__all__ = [
    "CCXError",
    "CCXValidationError",
    "CCXIntegrityError",
    "CCXSecurityError",
    "Manifest",
    "GraphEntry",
    "AssetEntry",
    "load_manifest",
    "CCXPackage",
    "ValidationReport",
    "open_package",
    "PackageBuilder",
    "write_package",
    "generate_ed25519_keypair",
    "__version__",
]
