import io
import stat
import zipfile

import pytest

from ccx.container import Container
from ccx.errors import CCXSecurityError, CCXValidationError
from tests import fixtures


def test_open_and_read_known_entry():
    c = Container.open(fixtures.core_minimal())
    assert c.has("manifest.json")
    assert c.read("mimetype") == b"application/vnd.ccx+zip"


def test_check_mimetype_ok():
    c = Container.open(fixtures.core_minimal())
    c.check_mimetype()  # no exception


def test_missing_mimetype_rejected():
    c = Container.open(fixtures.missing_mimetype())
    with pytest.raises(CCXValidationError):
        c.check_mimetype()


def test_path_traversal_rejected_on_open():
    with pytest.raises(CCXSecurityError):
        Container.open(fixtures.path_traversal())


def test_not_a_zip_rejected():
    with pytest.raises(CCXValidationError):
        Container.open(b"this is not a zip")


def test_entry_size_limit(monkeypatch):
    import ccx.container as mod

    monkeypatch.setattr(mod, "MAX_ENTRY_UNCOMPRESSED", 4)
    with pytest.raises(CCXSecurityError):
        Container.open(fixtures.core_minimal())  # entries exceed the 4-byte cap


def _raw_zip(entries, *, symlink_name=None):
    """Build raw zip bytes from (name, data) pairs; mark symlink_name as a symlink."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name)
            if symlink_name is not None and name == symlink_name:
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, data)
    return buf.getvalue()


_MIME = ("mimetype", b"application/vnd.ccx+zip")


def test_absolute_path_rejected():
    data = _raw_zip([_MIME, ("/etc/passwd", b"x")])
    with pytest.raises(CCXSecurityError):
        Container.open(data)


def test_drive_letter_path_rejected():
    data = _raw_zip([_MIME, ("C:/windows/system32", b"x")])
    with pytest.raises(CCXSecurityError):
        Container.open(data)


def test_symlink_entry_rejected():
    data = _raw_zip([_MIME, ("link", b"/etc/passwd")], symlink_name="link")
    with pytest.raises(CCXSecurityError):
        Container.open(data)


def test_too_many_entries_rejected(monkeypatch):
    import ccx.container as mod

    monkeypatch.setattr(mod, "MAX_ENTRIES", 1)
    with pytest.raises(CCXSecurityError):
        Container.open(fixtures.core_minimal())


def test_total_size_limit(monkeypatch):
    import ccx.container as mod

    monkeypatch.setattr(mod, "MAX_TOTAL_UNCOMPRESSED", 1)
    with pytest.raises(CCXSecurityError):
        Container.open(fixtures.core_minimal())


def test_read_wraps_decompression_error(monkeypatch):
    import zlib

    c = Container.open(fixtures.core_minimal())

    def boom(*args, **kwargs):
        raise zlib.error("corrupt")

    monkeypatch.setattr(c._zf, "read", boom)
    with pytest.raises(CCXValidationError):
        c.read("manifest.json")
