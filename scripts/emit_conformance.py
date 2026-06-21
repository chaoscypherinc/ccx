"""Emit the canonical conformance fixture packages into conformance/.

Run from the repo root:  python scripts/emit_conformance.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so that `tests` is importable.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests import fixtures

VALID = ROOT / "conformance" / "valid"
INVALID = ROOT / "conformance" / "invalid"


def main() -> None:
    VALID.mkdir(parents=True, exist_ok=True)
    INVALID.mkdir(parents=True, exist_ok=True)
    (VALID / "core-minimal.ccx").write_bytes(fixtures.core_minimal())
    (VALID / "core-with-app-graph.ccx").write_bytes(fixtures.core_with_app_graph())
    (VALID / "sources-minimal.ccx").write_bytes(fixtures.sources_minimal())
    (VALID / "sources-inline-chunk.ccx").write_bytes(fixtures.sources_inline_chunk())
    (VALID / "sources-only.ccx").write_bytes(fixtures.sources_only())
    (VALID / "embeddings-minimal.ccx").write_bytes(fixtures.embeddings_minimal())
    (VALID / "signed-minimal.ccx").write_bytes(fixtures.signed_minimal())
    (VALID / "shapes-minimal.ccx").write_bytes(fixtures.shapes_minimal())
    for name, builder in fixtures.INVALID_BUILDERS.items():
        (INVALID / f"{name}.ccx").write_bytes(builder())
    print(f"wrote fixtures to {VALID} and {INVALID}")


if __name__ == "__main__":
    main()
