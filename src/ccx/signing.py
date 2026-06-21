"""Signing and offline verification for the Signed conformance class.

Two formats, both verified **offline** (no network at read time) and **fail
closed** (any error or missing dependency yields ``verified=False`` with a
reason):

- ``ed25519`` — self-managed detached signatures over the manifest bytes. Simple,
  fully offline, no PKI. Requires the ``signed`` extra (``cryptography``). The
  public key travels in the manifest, so a verified ed25519 signature proves
  "signed by the holder of *this* key + unaltered"; binding the key to a real
  identity is the verifier's job (pin/trust the key out-of-band, like SSH/minisign).
- ``sigstore`` — identity-bound bundles (OIDC identity via Fulcio + Rekor
  transparency). Verification is delegated to ``sigstore-python`` (the ``sigstore``
  extra) using a caller-supplied **offline** trusted root; CCX never reaches the
  network at read time. See ``verify_sigstore``.
"""

from __future__ import annotations

import base64

# Crypto-agility / post-quantum readiness: `signatures[].format` is an open
# discriminator and `signatures[]` is a list, so adding a NIST post-quantum scheme
# (FIPS 204 ML-DSA, FIPS 205 SLH-DSA) is a new format value — not a format change —
# and a package MAY carry hybrid classical+PQC signatures (e.g. ed25519 + ml-dsa).
# SHA-256/512 checksums are already post-quantum-safe (Grover is only quadratic).
# These are RESERVED and recognised by the verify dispatch, but not yet implemented
# (no maintained Python binding for ML-DSA/SLH-DSA is available yet).
RESERVED_PQC_FORMATS = ("ml-dsa-44", "ml-dsa-65", "ml-dsa-87", "slh-dsa-128s", "slh-dsa-256s")


def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    """Generate a new Ed25519 keypair as ``(private_raw, public_raw)`` (32 bytes
    each). Requires the ``signed`` extra (``pip install ccx-format[signed]``)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    private_raw = private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return private_raw, public_raw


def public_key_b64(private_key_raw: bytes) -> str:
    """Return the base64 public key for a raw Ed25519 private key."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    public = Ed25519PrivateKey.from_private_bytes(private_key_raw).public_key()
    raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def sign_ed25519(message: bytes, private_key_raw: bytes) -> bytes:
    """Sign *message* with a raw Ed25519 private key. Ed25519 is deterministic, so
    the signature is reproducible for a given (key, message)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.from_private_bytes(private_key_raw).sign(message)


def verify_ed25519(message: bytes, signature: bytes, public_key_b64_str: str) -> tuple[bool, str | None]:
    """Verify a detached Ed25519 signature over *message*. Fails closed."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        return False, "ed25519 verification requires the 'signed' extra (cryptography)"
    try:
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64_str))
    except Exception as exc:  # noqa: BLE001 - any decoding failure is a verification failure
        return False, f"invalid public key: {exc}"
    try:
        public.verify(signature, message)
        return True, None
    except InvalidSignature:
        return False, "signature does not verify"
    except Exception as exc:  # noqa: BLE001
        return False, f"verification error: {exc}"


def verify_sigstore(message: bytes, bundle_bytes: bytes) -> tuple[bool, str | None, str | None]:
    """Verify a Sigstore bundle over *message*, **offline**. Returns
    ``(verified, identity, error)``; fails closed.

    Delegated to ``sigstore-python`` (the ``signed-sigstore`` extra). Offline
    verification requires a pinned trusted root — CCX never fetches one at read
    time. This integration point is the shape Lexicon's hub builds its identity
    policy around; it is intentionally fail-closed and is exercised against
    ``sigstore-python`` in integration (not in the unit suite, which has no
    ``sigstore`` install or real bundle).
    """
    try:
        import sigstore  # noqa: F401
    except ImportError:
        return False, None, "sigstore verification requires the 'signed-sigstore' extra"
    # A correct offline verification supplies a pinned TrustedRoot and an identity
    # policy. Until that policy is wired (with Lexicon's identity model), refuse
    # rather than risk a network call or a false pass.
    return False, None, (
        "sigstore verification is not yet wired to an offline trusted root; "
        "the bundle is carried for external/Lexicon verification"
    )
