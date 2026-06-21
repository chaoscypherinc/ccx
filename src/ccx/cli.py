"""Command-line interface: `ccx inspect` and `ccx validate`."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path

from .errors import CCXError
from .package import open_package
from .writer import PackageBuilder


def _cmd_inspect(args: argparse.Namespace) -> int:
    try:
        pkg = open_package(args.path)
    except CCXError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    m = pkg.manifest
    print(f"name:    {m.name}")
    print(f"version: {m.package_version} (ccx {m.ccx_version})")
    if m.license:
        print(f"license: {m.license}")
    print(f"graphs:  {len(m.graphs)}")
    for g in m.graphs:
        default = " [default]" if (g.role == "default" or g.namespace == "ccx") else ""
        print(f"  - {g.namespace}.{g.name}{default}  ({g.path})")
    print(f"assets:  {len(m.assets)}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        pkg = open_package(args.path)
    except CCXError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    report = pkg.validate()
    for w in report.warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in report.errors:
        print(f"error: {e}", file=sys.stderr)
    if report.ok:
        print(f"VALID ({report.conformance_level})")
        return 0
    print("INVALID", file=sys.stderr)
    return 1


def _cmd_pack(args: argparse.Namespace) -> int:
    src = Path(args.path)
    try:
        meta_path = src / "manifest.json"
        if not meta_path.is_file():
            raise CCXError(f"missing {meta_path}")
        meta = json.loads(meta_path.read_text("utf-8"))
        meta.pop("graphs", None)
        meta.pop("assets", None)
        meta.pop("ccx_version", None)
        builder = PackageBuilder(**meta)

        knowledge = src / "knowledge.jsonld"
        if knowledge.is_file():
            builder.add_graph("ccx", "knowledge", json.loads(knowledge.read_text("utf-8")),
                              role="default")
        graphs_dir = src / "graphs"
        if graphs_dir.is_dir():
            for f in sorted(graphs_dir.glob("*.jsonld")):
                if "." not in f.stem:
                    raise CCXError(
                        f"graph file {f.name!r} must be named '<namespace>.<name>.jsonld'"
                    )
                namespace, name = f.stem.split(".", 1)
                builder.add_graph(namespace, name, json.loads(f.read_text("utf-8")))
        context_file = src / "context.jsonld"
        if context_file.is_file():
            builder.set_context(json.loads(context_file.read_text("utf-8")))
        assets_dir = src / "assets"
        if assets_dir.is_dir():
            for f in sorted(p for p in assets_dir.rglob("*") if p.is_file()):
                rel = f.relative_to(src).as_posix()
                media_type = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                builder.add_asset(f.read_bytes(), media_type, path=rel)

        builder.write(args.output)
    except CCXError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccx", description="CCX (Chaos Cypher eXchange) reader")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="print a package's manifest summary")
    p_inspect.add_argument("path", help="path to a .ccx file")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_validate = sub.add_parser("validate", help="validate a package (Core conformance)")
    p_validate.add_argument("path", help="path to a .ccx file")
    p_validate.set_defaults(func=_cmd_validate)

    p_pack = sub.add_parser("pack", help="assemble a .ccx from a prepared directory")
    p_pack.add_argument("path", help="source directory (manifest.json + knowledge.jsonld + graphs/ + assets/)")
    p_pack.add_argument("-o", "--output", required=True, help="output .ccx path")
    p_pack.set_defaults(func=_cmd_pack)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
