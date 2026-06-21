"""High-level CCX package object: open, inspect, validate (Core level)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import conformance as _conf
from . import graphs as _graphs
from .checksums import verify
from .constants import CCX_VERSION, CONTEXT_PATH, MANIFEST_PATH, SHAPES_PATH, SOURCES_PATH
from .container import Container
from .errors import CCXError, CCXSecurityError, CCXValidationError
from .manifest import Manifest, load_manifest

_UNSET = object()


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conformance_level: str | None = None
    classes: tuple[str, ...] = ()


@dataclass
class GraphDocument:
    namespace: str
    name: str
    role: str | None
    path: str
    doc: dict


class CCXPackage:
    """An opened CCX package. The manifest is parsed eagerly; graphs are lazy."""

    def __init__(self, container: Container, manifest: Manifest):
        self.container = container
        self.manifest = manifest
        self._dataset = None
        self._context = _UNSET

    def context(self) -> dict:
        if self._context is _UNSET:
            raw = self.container.read(CONTEXT_PATH).decode("utf-8")
            try:
                self._context = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CCXValidationError(
                    f"{CONTEXT_PATH} is not valid JSON: {exc}"
                ) from exc
        return self._context

    def dataset(self):
        if self._dataset is None:
            self._dataset = _graphs.load_dataset(self.container, self.manifest)
        return self._dataset

    def validate(self) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []

        try:
            self.container.check_mimetype()
        except CCXError as exc:
            errors.append(str(exc))

        if self.manifest.ccx_version != CCX_VERSION:
            warnings.append(
                f"ccx_version {self.manifest.ccx_version!r} != supported {CCX_VERSION!r}"
            )

        if not self.container.has(CONTEXT_PATH):
            errors.append(f"missing {CONTEXT_PATH}")
        else:
            try:
                context_doc = self.context()
            except CCXValidationError as exc:
                errors.append(str(exc))
            else:
                try:
                    _graphs.reject_remote_context(context_doc)
                except CCXSecurityError as exc:
                    errors.append(f"{CONTEXT_PATH}: {exc}")

        if not self.manifest.graphs:
            errors.append("no graphs declared")
        elif not any(_graphs.is_default(g) for g in self.manifest.graphs):
            warnings.append("no default/core graph (role='default' or namespace='ccx')")

        graph_paths = {g.path for g in self.manifest.graphs}
        for entry in self.manifest.graphs + self.manifest.assets:
            if not self.container.has(entry.path):
                errors.append(f"declared file missing: {entry.path}")
                continue
            data = self.container.read(entry.path)
            if not verify(data, entry.sha256, entry.sha512):
                errors.append(f"checksum mismatch: {entry.path}")
                continue
            if entry.path in graph_paths:
                try:
                    doc = json.loads(data.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    errors.append(f"{entry.path} is not valid JSON: {exc}")
                    continue
                try:
                    _graphs.reject_remote_context(doc)
                except CCXSecurityError as exc:
                    errors.append(f"{entry.path}: {exc}")

        if self.manifest.license is None:
            warnings.append("no license declared (recommended)")

        ok = not errors
        classes: list[str] = []
        if ok:
            classes.append("core")
            for cls_name, checker in _conf.CHECKERS:
                present, issues = checker(self)
                if not present:
                    continue
                if issues:
                    warnings.extend(f"{cls_name}: {issue}" for issue in issues)
                else:
                    classes.append(cls_name)
        return ValidationReport(
            ok=ok,
            errors=errors,
            warnings=warnings,
            conformance_level="core" if ok else None,
            classes=tuple(classes),
        )

    def graph_documents(self) -> list[GraphDocument]:
        """Return each declared graph's raw on-disk JSON-LD document (as dicts)."""
        out: list[GraphDocument] = []
        for g in self.manifest.graphs:
            raw = self.container.read(g.path).decode("utf-8")
            try:
                doc = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CCXValidationError(
                    f"{g.path} is not valid JSON: {exc}"
                ) from exc
            out.append(
                GraphDocument(
                    namespace=g.namespace,
                    name=g.name,
                    role=g.role,
                    path=g.path,
                    doc=doc,
                )
            )
        return out

    def asset_bytes(self, path: str) -> bytes:
        """Return the raw bytes of a declared asset by its manifest path."""
        if not any(a.path == path for a in self.manifest.assets):
            raise CCXValidationError(f"no such declared asset: {path!r}")
        return self.container.read(path)

    def sources(self) -> list[dict]:
        """Parse `sources.jsonl` (Core + Sources) into records. Returns [] if absent."""
        if not self.container.has(SOURCES_PATH):
            return []
        raw = self.container.read(SOURCES_PATH).decode("utf-8")
        out: list[dict] = []
        for n, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise CCXValidationError(
                    f"{SOURCES_PATH} line {n} is not valid JSON: {exc}"
                ) from exc
        return out

    def shapes(self) -> str | None:
        """Return the `shapes.ttl` Turtle text (Shapes class), or None if absent."""
        if not self.container.has(SHAPES_PATH):
            return None
        return self.container.read(SHAPES_PATH).decode("utf-8")

    def shacl_validate(self):
        """Validate the package's graphs against `shapes.ttl` using pyshacl.

        Requires the optional `shapes` extra (``pip install ccx-format[shapes]``).
        Returns ``(conforms: bool, report_text: str)``.
        """
        text = self.shapes()
        if text is None:
            raise CCXValidationError("package has no shapes.ttl to validate against")
        try:
            import pyshacl
        except ImportError as exc:
            raise CCXValidationError(
                "SHACL validation requires the 'shapes' extra: "
                "pip install ccx-format[shapes]"
            ) from exc
        import rdflib

        shapes_graph = rdflib.Graph().parse(data=text, format="turtle")
        conforms, _report_graph, report_text = pyshacl.validate(
            self.dataset(), shacl_graph=shapes_graph, inference="none"
        )
        return conforms, report_text

    def embeddings(self) -> list[dict]:
        """Return the manifest embedding descriptors (Embeddings class). [] if none."""
        return list(self.manifest.raw.get("embeddings", []))

    def read_embeddings(self, descriptor: dict):
        """Read an `included` embedding sidecar into a pyarrow Table.

        Requires the optional `embeddings` extra (``pip install
        ccx-format[embeddings]``).
        """
        path = descriptor.get("path")
        if not descriptor.get("included") or not path:
            raise CCXValidationError("descriptor has no included sidecar to read")
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise CCXValidationError(
                "reading embedding sidecars requires the 'embeddings' extra: "
                "pip install ccx-format[embeddings]"
            ) from exc
        import io

        return pq.read_table(io.BytesIO(self.container.read(path)))

    def verify_signatures(self) -> list[dict]:
        """Verify each declared signature over the raw `manifest.json` bytes.

        Offline and fail-closed. Returns one dict per signature:
        ``{path, format, verified, error}`` plus ``key`` (ed25519) or ``identity``
        (sigstore). Dispatch is by `signatures[].format` (crypto-agile): `ed25519`
        (requires the `signed` extra), `sigstore` (requires `signed-sigstore`), and
        the reserved post-quantum formats (ML-DSA / SLH-DSA), which are recognised
        but not yet implemented in the reference reader.
        """
        from . import signing

        entries = self.manifest.raw.get("signatures") or []
        manifest_bytes = self.container.read(MANIFEST_PATH)
        results: list[dict] = []
        for entry in entries:
            path = entry.get("path")
            fmt = entry.get("format")
            result: dict = {"path": path, "format": fmt, "verified": False, "error": None}
            if not path or not self.container.has(path):
                result["error"] = f"signature file missing: {path!r}"
                results.append(result)
                continue
            sig_bytes = self.container.read(path)
            if fmt == "ed25519":
                ok, err = signing.verify_ed25519(
                    manifest_bytes, sig_bytes, entry.get("public_key", "")
                )
                result["verified"], result["error"] = ok, err
                result["key"] = entry.get("public_key")
            elif fmt == "sigstore":
                ok, identity, err = signing.verify_sigstore(manifest_bytes, sig_bytes)
                result["verified"], result["identity"], result["error"] = ok, identity, err
            elif fmt in signing.RESERVED_PQC_FORMATS:
                result["error"] = (
                    f"post-quantum format {fmt!r} is reserved but not yet implemented"
                )
            else:
                result["error"] = f"unsupported signature format: {fmt!r}"
            results.append(result)
        return results


def open_package(source: str | Path | bytes | bytearray) -> CCXPackage:
    """Open a .ccx package from a path (str/Path) or raw bytes."""
    container = Container.open(source)
    if not container.has(MANIFEST_PATH):
        raise CCXValidationError(f"missing {MANIFEST_PATH}")
    raw = container.read(MANIFEST_PATH).decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CCXValidationError(f"{MANIFEST_PATH} is not valid JSON: {exc}") from exc
    manifest = load_manifest(data)
    return CCXPackage(container, manifest)
