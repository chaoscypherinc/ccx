"""The bundled minimal canonical CCX @context."""

from __future__ import annotations

import copy
import json
from importlib.resources import files

_CONTEXT: dict | None = None


def default_context() -> dict:
    """Return a fresh copy of the bundled canonical CCX @context document."""
    global _CONTEXT
    if _CONTEXT is None:
        text = files("ccx.schemas").joinpath("context.jsonld").read_text("utf-8")
        _CONTEXT = json.loads(text)
    return copy.deepcopy(_CONTEXT)
