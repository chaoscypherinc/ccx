"""Reference writer: assemble graphs + assets + metadata into a valid .ccx."""

from __future__ import annotations

import copy
import io
import json
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import rdflib

from . import graphs as _graphs
from .checksums import compute, sha256_hex
from .constants import (
    CCX_VERSION,
    CONTEXT_PATH,
    MANIFEST_PATH,
    MEDIA_TYPE_JSONL,
    MEDIA_TYPE_JSONLD,
    MEDIA_TYPE_TURTLE,
    MIMETYPE,
    MIMETYPE_PATH,
    SHAPES_PATH,
    SIGNATURE_PATH,
    SOURCES_PATH,
)
from .context import default_context
from .errors import CCXValidationError
from .manifest import validate_manifest_data

_ZIP_DATE = (1980, 1, 1, 0, 0, 0)
_FILE_ATTR = 0o100644 << 16  # S_IFREG | rw-r--r--


def _default_generator() -> str:
    try:
        return f"ccx-format@{version('ccx-format')}"
    except PackageNotFoundError:  # pragma: no cover
        return "ccx-format"


def _dumps(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _is_default(namespace: str, role: str | None) -> bool:
    return role == "default" or namespace == "ccx"


class PackageBuilder:
    """Incrementally assemble a CCX 3.0 package, then build() to validated bytes."""

    def __init__(
        self,
        *,
        name: str,
        package_version: str,
        license: str | None = None,
        base_iri: str | None = None,
        title: str | None = None,
        description: str | None = None,
        author: str | None = None,
        tags: list[str] | None = None,
        derived_from: dict | None = None,
        dependencies: dict | None = None,
        created_at: str | None = None,
        generator: str | None = None,
    ):
        self.name = name
        self.package_version = package_version
        self.license = license
        self.base_iri = base_iri
        self.title = title
        self.description = description
        self.author = author
        self.tags = list(tags) if tags else None
        self.derived_from = dict(derived_from) if derived_from else None
        self.dependencies = dict(dependencies) if dependencies else None
        self.created_at = created_at
        self.generator = generator
        self._graphs: list[tuple[str, str, str | None, object]] = []
        self._assets: dict[str, tuple[str, bytes, dict]] = {}
        self._sources: list[dict] = []
        self._embeddings: list[dict] = []
        self._sign: tuple[bytes, str] | None = None
        self._context = default_context()

    def with_version(self, new_version: str) -> "PackageBuilder":
        """Set the package version (chainable)."""
        self.package_version = new_version
        return self

    def extend_context(self, terms: dict) -> "PackageBuilder":
        _graphs.reject_remote_context({"@context": terms})
        self._context["@context"].update(terms)
        return self

    def set_context(self, context: dict) -> "PackageBuilder":
        if "@context" not in context:
            raise CCXValidationError("context document must contain an '@context' key")
        _graphs.reject_remote_context(context)
        self._context = copy.deepcopy(context)
        return self

    def add_graph(self, namespace: str, name: str, content, *, role: str | None = None) -> "PackageBuilder":
        if role not in (None, "default"):
            raise CCXValidationError(
                f"unsupported graph role {role!r}; only None or 'default' are allowed"
            )
        for label, value in (("namespace", namespace), ("name", name)):
            if "/" in value or ".." in value:
                raise CCXValidationError(
                    f"invalid graph {label} {value!r}: '/' and '..' are not allowed"
                )
        if namespace == "ccx" and name != "knowledge":
            raise CCXValidationError(
                "the 'ccx' namespace is reserved for the default 'knowledge' graph"
            )
        if role == "default" and (namespace, name) != ("ccx", "knowledge"):
            raise CCXValidationError(
                "role='default' is only valid for the ccx/knowledge graph"
            )
        self._graphs.append((namespace, name, role, content))
        return self

    def add_asset(
        self,
        data: bytes,
        media_type: str,
        *,
        path: str | None = None,
        source_mode: str | None = None,
        license: str | None = None,
    ) -> str:
        if path is None:
            path = f"assets/sha256/{sha256_hex(data)}"
        extra: dict = {}
        if source_mode is not None:
            extra["source_mode"] = source_mode
        if license is not None:
            extra["license"] = license
        existing = self._assets.get(path)
        if existing is not None and existing[1] != data:
            raise CCXValidationError(f"conflicting asset content for path {path!r}")
        self._assets[path] = (media_type, data, extra)
        return path

    def add_source(
        self,
        record: dict,
        *,
        text: bytes | None = None,
        media_type: str = "text/plain",
        source_mode: str | None = None,
    ) -> "PackageBuilder":
        """Add a `sources.jsonl` record (Core + Sources). If *text* is given, it is
        stored as a content-addressed asset (with *source_mode*) and the record's
        `text` field is set to that asset path."""
        rec = dict(record)
        if text is not None:
            rec.setdefault(
                "text",
                self.add_asset(text, media_type, source_mode=source_mode or "derived-only"),
            )
        self._sources.append(rec)
        return self

    def add_shapes(self, ttl: bytes) -> "PackageBuilder":
        """Add a `shapes.ttl` SHACL shapes graph (Shapes class)."""
        self.add_asset(ttl, MEDIA_TYPE_TURTLE, path=SHAPES_PATH)
        return self

    def add_embeddings(
        self,
        descriptor: dict,
        *,
        sidecar: bytes | None = None,
        media_type: str = "application/vnd.apache.parquet",
    ) -> "PackageBuilder":
        """Add an embedding descriptor (Embeddings class). If *sidecar* bytes are
        given, they are stored as a content-addressed asset, the descriptor's
        `path` is set to it, and `included` defaults to True."""
        desc = dict(descriptor)
        if sidecar is not None:
            desc.setdefault("path", self.add_asset(sidecar, media_type))
            desc.setdefault("included", True)
        self._embeddings.append(desc)
        return self

    def sign(self, private_key: bytes, *, path: str = SIGNATURE_PATH) -> "PackageBuilder":
        """Sign the manifest with a raw Ed25519 private key (Signed class).

        The detached signature is written at *path* and the public key is embedded
        in the manifest `signatures` entry; verification is fully offline. Requires
        the `signed` extra (cryptography). Editing a package invalidates its
        signature, so call ``sign`` as the final step before ``build``. (Other
        formats — sigstore, post-quantum — are verified by the reader but produced
        by external tooling; see signing.py.)
        """
        self._sign = (private_key, path)
        return self

    def _resolve_doc(self, content) -> dict:
        if isinstance(content, dict):
            doc = dict(content)
            if "@context" not in doc:
                doc["@context"] = self._context["@context"]
            return doc
        if isinstance(content, (rdflib.Graph, rdflib.Dataset)):
            try:
                serialized = content.serialize(
                    format="json-ld", context=self._context["@context"], auto_compact=True
                )
            except Exception as exc:  # noqa: BLE001 - surface a uniform error
                raise CCXValidationError(f"failed to serialize rdflib graph: {exc}") from exc
            doc = json.loads(serialized)
            if isinstance(doc, list):
                doc = {"@graph": doc}
            doc["@context"] = self._context["@context"]
            return doc
        raise CCXValidationError(
            "add_graph content must be a JSON-LD dict or an rdflib Graph/Dataset"
        )

    def _graph_path(self, namespace: str, name: str, role: str | None) -> str:
        if _is_default(namespace, role):
            return "knowledge.jsonld"
        return f"graphs/{namespace}.{name}.jsonld"

    def _manifest(self, graph_entries: list[dict], asset_entries: list[dict]) -> dict:
        m: dict = {
            "ccx_version": CCX_VERSION,
            "name": self.name,
            "package_version": self.package_version,
            "graphs": graph_entries,
            "assets": asset_entries,
            "generator": self.generator or _default_generator(),
        }
        for key, value in (
            ("license", self.license),
            ("base_iri", self.base_iri),
            ("title", self.title),
            ("description", self.description),
            ("author", self.author),
            ("tags", self.tags),
            ("derived_from", self.derived_from),
            ("dependencies", self.dependencies),
            ("created_at", self.created_at),
        ):
            if value is not None:
                m[key] = value
        return m

    def build(self) -> bytes:
        if not self._graphs:
            raise CCXValidationError("a package must declare at least one graph")

        files: list[tuple[str, bytes, bool]] = []
        files.append((MIMETYPE_PATH, MIMETYPE.encode("utf-8"), True))
        files.append((CONTEXT_PATH, _dumps(self._context), False))

        graph_entries: list[dict] = []
        seen_paths: set[str] = set()
        for namespace, name, role, content in self._graphs:
            doc = self._resolve_doc(content)
            _graphs.reject_remote_context(doc)
            data = _dumps(doc)
            path = self._graph_path(namespace, name, role)
            if path in seen_paths:
                raise CCXValidationError(
                    f"duplicate graph path {path!r} (namespace/name collision)"
                )
            seen_paths.add(path)
            s256, s512 = compute(data)
            entry = {
                "namespace": namespace,
                "name": name,
                "path": path,
                "media_type": MEDIA_TYPE_JSONLD,
                "sha256": s256,
                "sha512": s512,
            }
            if _is_default(namespace, role):
                entry["role"] = "default"
            graph_entries.append(entry)
            files.append((path, data, False))

        if self._sources:
            lines = [json.dumps(r, sort_keys=True, ensure_ascii=False) for r in self._sources]
            jsonl = ("\n".join(lines) + "\n").encode("utf-8")
            self._assets[SOURCES_PATH] = (MEDIA_TYPE_JSONL, jsonl, {})

        asset_entries: list[dict] = []
        reserved_paths = {MIMETYPE_PATH, CONTEXT_PATH, MANIFEST_PATH} | seen_paths
        for path in sorted(self._assets):
            if path in reserved_paths:
                raise CCXValidationError(
                    f"asset path {path!r} collides with a reserved or graph path"
                )
            media_type, asset_data, extra = self._assets[path]
            s256, s512 = compute(asset_data)
            entry = {"path": path, "media_type": media_type, "sha256": s256, "sha512": s512}
            entry.update(extra)
            asset_entries.append(entry)
            files.append((path, asset_data, False))

        manifest = self._manifest(graph_entries, asset_entries)
        if self._embeddings:
            manifest["embeddings"] = self._embeddings
        if self._sign is not None:
            from . import signing

            private_key, sig_path = self._sign
            manifest["signatures"] = [
                {
                    "path": sig_path,
                    "format": "ed25519",
                    "public_key": signing.public_key_b64(private_key),
                }
            ]
        validate_manifest_data(manifest)
        manifest_bytes = _dumps(manifest)
        files.append((MANIFEST_PATH, manifest_bytes, False))
        if self._sign is not None:
            from . import signing

            private_key, sig_path = self._sign
            files.append((sig_path, signing.sign_ed25519(manifest_bytes, private_key), False))

        data = _assemble_zip(files)
        _self_validate(data)
        return data

    @classmethod
    def from_package(cls, pkg) -> "PackageBuilder":
        """Reconstruct a builder from a read package for an edit→re-write cycle.

        Metadata (including ``generator``) is preserved verbatim so a no-change
        rebuild is byte-identical. After an edit, ``generator`` still reflects the
        ORIGINAL producer; set ``builder.generator = None`` to re-stamp it with the
        default ``ccx-format@<version>`` on the next build.
        """
        m = pkg.manifest
        builder = cls(
            name=m.name,
            package_version=m.package_version,
            license=m.license,
            base_iri=m.base_iri,
            title=m.title,
            description=m.description,
            author=m.author,
            tags=list(m.raw["tags"]) if m.raw.get("tags") is not None else None,
            derived_from=dict(m.raw["derived_from"]) if m.raw.get("derived_from") is not None else None,
            dependencies=dict(m.raw["dependencies"]) if m.raw.get("dependencies") is not None else None,
            created_at=m.created_at,
            generator=m.generator,
        )
        builder.set_context(pkg.context())
        for gd in pkg.graph_documents():
            builder.add_graph(gd.namespace, gd.name, gd.doc, role=gd.role)
        raw_assets = {a["path"]: a for a in m.raw.get("assets", [])}
        for asset in m.assets:
            raw = raw_assets.get(asset.path, {})
            builder.add_asset(
                pkg.asset_bytes(asset.path),
                asset.media_type,
                path=asset.path,
                source_mode=raw.get("source_mode"),
                license=raw.get("license"),
            )
        builder._embeddings = [dict(e) for e in m.raw.get("embeddings", [])]
        return builder

    def write(self, path) -> None:
        """Build the package and write the bytes to *path*."""
        Path(path).write_bytes(self.build())


def write_package(path, *, name: str, package_version: str, graphs, assets=None, **metadata) -> None:
    """Convenience: build a package from graph tuples ``(namespace, name, content[, role])``
    and asset tuples ``(data, media_type[, path])``, and write it to *path*."""
    builder = PackageBuilder(name=name, package_version=package_version, **metadata)
    for g in graphs:
        namespace, gname, content = g[0], g[1], g[2]
        role = g[3] if len(g) > 3 else None
        builder.add_graph(namespace, gname, content, role=role)
    for a in assets or []:
        data, media_type = a[0], a[1]
        asset_path = a[2] if len(a) > 2 else None
        builder.add_asset(data, media_type, path=asset_path)
    builder.write(path)


def _assemble_zip(files: list[tuple[str, bytes, bool]]) -> bytes:
    """Assemble a deterministic ZIP. Byte-identical for identical inputs within a
    given zlib version; cross-zlib-version byte-identity is not guaranteed."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for arcname, data, stored in files:
            info = zipfile.ZipInfo(filename=arcname, date_time=_ZIP_DATE)
            info.external_attr = _FILE_ATTR
            info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    return buf.getvalue()


def _self_validate(data: bytes) -> None:
    from .package import open_package

    report = open_package(data).validate()
    if not report.ok:
        raise CCXValidationError(
            "writer produced a non-conformant package: " + "; ".join(report.errors)
        )
