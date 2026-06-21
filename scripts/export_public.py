#!/usr/bin/env python3
"""Build a clean public export tree of this repo for ``chaoscypherinc/ccx``.

The public repository only ever receives **clean exports**: no private git
history and no ``internal/`` material. This mirrors the chaoscypher
public-clean-export process.

Usage::

    python scripts/export_public.py --out ../ccx-public-export

The script only **stages + verifies** the tree; it never pushes. Then:

* **Seed** an empty public repo: ``git init`` the staged tree, make a single
  clean commit, and push.
* **Update** an existing public repo: never force-push (it breaks every clone
  and fork) — accrue one summarized commit onto a clone of public ``main``
  (see ``internal/procedures/public-release.md`` when publishing is set up).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Dev-only directory names that MUST NOT appear in the public repo.
EXCLUDE_DIRS = {
    ".git",
    "internal",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "__pycache__",
}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".egg-info")

REPO_ROOT = Path(__file__).resolve().parent.parent


def _ignore(_dir: str, names: list[str]) -> set[str]:
    """``shutil.copytree`` ignore callback — drop dev-only paths."""
    ignored: set[str] = set()
    for name in names:
        if name in EXCLUDE_DIRS or name.endswith(EXCLUDE_SUFFIXES):
            ignored.add(name)
    return ignored


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a clean public export of ccx-dev."
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output directory (created fresh; must be outside the repo).",
    )
    args = parser.parse_args()

    out = args.out.resolve()
    if out == REPO_ROOT or REPO_ROOT in out.parents or out in REPO_ROOT.parents:
        print("error: --out must be a separate directory outside the repo", file=sys.stderr)
        return 2

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(REPO_ROOT, out, ignore=_ignore)

    # Verify the export is clean before anyone can push it.
    leaks = [p for p in ("internal", ".git") if (out / p).exists()]
    if leaks:
        print(f"error: export still contains private paths: {leaks}", file=sys.stderr)
        return 1

    print(f"OK: clean public tree at {out}")
    print("review it, then publish (this script never pushes):")
    print("  SEED an empty public repo:")
    print(f"    cd {out} && git init -b main && git add . && git commit -m 'chore: public export'")
    print("    git remote add origin https://github.com/chaoscypherinc/ccx.git && git push -u origin main")
    print("  UPDATE an existing public repo: accrue ONE summarized commit onto a clone of")
    print("    public main — never force-push (see internal/procedures/public-release.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
