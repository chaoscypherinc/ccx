import io
import zipfile

from tests import fixtures


def test_core_minimal_is_a_zip_with_mimetype_first():
    data = fixtures.core_minimal()
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = zf.namelist()
    assert names[0] == "mimetype"
    assert set(names) >= {"mimetype", "context.jsonld", "knowledge.jsonld", "manifest.json"}
    assert zf.read("mimetype") == b"application/vnd.ccx+zip"


def test_bad_checksum_keeps_stale_hash():
    # The knowledge bytes are replaced but the manifest hash is NOT updated.
    data = fixtures.bad_checksum()
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert b"TAMPERED" in zf.read("knowledge.jsonld")


def test_invalid_variants_are_zips():
    for builder in fixtures.INVALID_BUILDERS.values():
        data = builder()
        assert isinstance(data, bytes) and data[:2] == b"PK"
