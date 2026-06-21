"""CCX manifest model and schema-validating loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib.resources import files

import jsonschema

from .errors import CCXValidationError

_SCHEMA: dict | None = None


def manifest_schema() -> dict:
    """Load and cache the bundled manifest JSON Schema."""
    global _SCHEMA
    if _SCHEMA is None:
        text = files("ccx.schemas").joinpath("manifest.schema.json").read_text("utf-8")
        _SCHEMA = json.loads(text)
    return _SCHEMA


@dataclass(frozen=True)
class GraphEntry:
    namespace: str
    name: str
    path: str
    media_type: str
    sha256: str
    sha512: str
    role: str | None = None


@dataclass(frozen=True)
class AssetEntry:
    path: str
    media_type: str
    sha256: str
    sha512: str


@dataclass(frozen=True)
class Manifest:
    ccx_version: str
    name: str
    package_version: str
    graphs: tuple[GraphEntry, ...]
    assets: tuple[AssetEntry, ...] = ()
    title: str | None = None
    description: str | None = None
    author: str | None = None
    license: str | None = None
    created_at: str | None = None
    base_iri: str | None = None
    generator: str | None = None
    raw: dict = field(default_factory=dict)


def validate_manifest_data(data: dict) -> None:
    """Raise CCXValidationError if *data* does not satisfy the manifest schema."""
    try:
        jsonschema.validate(data, manifest_schema())
    except jsonschema.ValidationError as exc:
        raise CCXValidationError(
            f"manifest.json failed schema validation at {exc.json_path}: {exc.message}"
        ) from exc


def load_manifest(data: dict) -> Manifest:
    """Validate *data* and build a Manifest."""
    validate_manifest_data(data)
    graphs = [
        GraphEntry(
            namespace=g["namespace"],
            name=g["name"],
            path=g["path"],
            media_type=g["media_type"],
            sha256=g["sha256"],
            sha512=g["sha512"],
            role=g.get("role"),
        )
        for g in data["graphs"]
    ]
    assets = [
        AssetEntry(
            path=a["path"],
            media_type=a["media_type"],
            sha256=a["sha256"],
            sha512=a["sha512"],
        )
        for a in data.get("assets", [])
    ]
    return Manifest(
        ccx_version=data["ccx_version"],
        name=data["name"],
        package_version=data["package_version"],
        graphs=tuple(graphs),
        assets=tuple(assets),
        title=data.get("title"),
        description=data.get("description"),
        author=data.get("author"),
        license=data.get("license"),
        created_at=data.get("created_at"),
        base_iri=data.get("base_iri"),
        generator=data.get("generator"),
        raw=dict(data),
    )
