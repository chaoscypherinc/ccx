"""Signed conformance class: ed25519 sign + offline verify, fail-closed dispatch,
and post-quantum readiness (crypto-agile format).

ed25519 is fully implemented and tested (cryptography is in the dev extra). The
sigstore and reserved post-quantum formats are recognised by the verify dispatch
and fail closed.
"""

from __future__ import annotations

import io
import zipfile

import ccx
from ccx import signing
from tests import fixtures


def _signed_package() -> bytes:
    private_key, _public = signing.generate_ed25519_keypair()
    builder = ccx.PackageBuilder(
        name="demo/people",
        package_version="1.0.0",
        license="CC-BY-4.0",
        base_iri="urn:ccx:demo:",
    )
    builder.add_graph("ccx", "knowledge", {"@graph": []}, role="default")
    builder.sign(private_key)
    return builder.build()


def _tamper_manifest(data: bytes, old: bytes, new: bytes) -> bytes:
    zin = zipfile.ZipFile(io.BytesIO(data), "r")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            content = zin.read(info.filename)
            if info.filename == "manifest.json":
                content = content.replace(old, new)
            ct = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            zout.writestr(info.filename, content, compress_type=ct)
    return out.getvalue()


def test_ed25519_signed_package_grants_signed_class():
    report = ccx.open_package(_signed_package()).validate()
    assert report.ok
    assert "signed" in report.classes


def test_verify_signatures_reports_ed25519_verified():
    results = ccx.open_package(_signed_package()).verify_signatures()
    assert len(results) == 1
    assert results[0]["format"] == "ed25519"
    assert results[0]["verified"] is True
    assert results[0]["key"]  # public key is surfaced for out-of-band pinning


def test_tampered_manifest_fails_verification_and_signed_class():
    tampered = _tamper_manifest(_signed_package(), b'"demo/people"', b'"demo/EVIL"')
    pkg = ccx.open_package(tampered)
    assert pkg.verify_signatures()[0]["verified"] is False
    report = pkg.validate()
    assert report.ok  # the manifest is still schema-valid + checksums match
    assert "signed" not in report.classes  # but the signature no longer verifies


def test_unsigned_package_has_no_signed_class():
    report = ccx.open_package(fixtures.core_minimal()).validate()
    assert "signed" not in report.classes
    assert ccx.open_package(fixtures.core_minimal()).verify_signatures() == []


def test_signed_minimal_fixture_verifies_and_grants_class():
    pkg = ccx.open_package(fixtures.signed_minimal())
    report = pkg.validate()
    assert report.ok
    assert "signed" in report.classes
    results = ccx.open_package(fixtures.signed_minimal()).verify_signatures()
    assert results[0]["format"] == "ed25519"
    assert results[0]["verified"] is True


def test_sigstore_verification_fails_closed_without_extra():
    # Without the signed-sigstore extra, sigstore verification must fail closed.
    verified, _identity, error = signing.verify_sigstore(b"manifest-bytes", b"bundle-bytes")
    assert verified is False
    assert "sigstore" in (error or "").lower()


def test_post_quantum_formats_are_reserved():
    # PQC readiness: the dispatch recognises ML-DSA / SLH-DSA as reserved future
    # formats (crypto-agility), even though no binding implements them yet.
    assert "ml-dsa-65" in signing.RESERVED_PQC_FORMATS
    assert "slh-dsa-128s" in signing.RESERVED_PQC_FORMATS
