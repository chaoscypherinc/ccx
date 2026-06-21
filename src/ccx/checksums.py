"""SHA-256 / SHA-512 helpers (base64-encoded digests), matching the manifest."""

from __future__ import annotations

import base64
import hashlib


def _b64(digest: bytes) -> str:
    return base64.b64encode(digest).decode("ascii")


def sha256_b64(data: bytes) -> str:
    return _b64(hashlib.sha256(data).digest())


def sha512_b64(data: bytes) -> str:
    return _b64(hashlib.sha512(data).digest())


def sha256_hex(data: bytes) -> str:
    """Hex SHA-256 digest, for content-addressed asset paths."""
    return hashlib.sha256(data).hexdigest()


def compute(data: bytes) -> tuple[str, str]:
    """Return (sha256_b64, sha512_b64) for *data*."""
    return sha256_b64(data), sha512_b64(data)


def verify(data: bytes, sha256: str, sha512: str) -> bool:
    """True iff both digests of *data* match the supplied base64 strings."""
    actual_256, actual_512 = compute(data)
    return actual_256 == sha256 and actual_512 == sha512
