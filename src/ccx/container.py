"""Safe access to a .ccx ZIP container."""

from __future__ import annotations

import io
import zipfile
import zlib
from pathlib import Path, PurePosixPath

from .constants import (
    MAX_ENTRIES,
    MAX_ENTRY_UNCOMPRESSED,
    MAX_TOTAL_UNCOMPRESSED,
    MIMETYPE,
    MIMETYPE_PATH,
)
from .errors import CCXSecurityError, CCXValidationError


class Container:
    """A hardened, read-only view over a .ccx ZIP archive."""

    def __init__(self, zf: zipfile.ZipFile):
        self._zf = zf
        self._names = zf.namelist()
        self._check_safety()

    @classmethod
    def open(cls, source: str | Path | bytes | bytearray) -> "Container":
        """Open from a filesystem path (str/Path) or raw bytes."""
        if isinstance(source, (bytes, bytearray)):
            buf = io.BytesIO(bytes(source))
        else:
            buf = io.BytesIO(Path(source).read_bytes())
        try:
            zf = zipfile.ZipFile(buf, "r")
        except zipfile.BadZipFile as exc:
            raise CCXValidationError(f"not a valid ZIP/.ccx file: {exc}") from exc
        return cls(zf)

    def _check_safety(self) -> None:
        infos = self._zf.infolist()
        if len(infos) > MAX_ENTRIES:
            raise CCXSecurityError(f"too many entries: {len(infos)} > {MAX_ENTRIES}")
        total = 0
        for info in infos:
            name = info.filename
            parts = PurePosixPath(name).parts
            # Python's ZipInfo normalizes os.sep/os.altsep to "/" on read, so backslash
            # traversal (`..\\evil`) is already collapsed to "/" here; PurePosixPath suffices.
            if name.startswith("/") or ".." in parts or (len(name) > 1 and name[1] == ":"):
                raise CCXSecurityError(f"unsafe path in archive: {name!r}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and (mode & 0xF000) == 0xA000:  # S_IFLNK
                raise CCXSecurityError(f"symlink not allowed: {name!r}")
            # CPython's ZipExtFile caps decompressed output at file_size, so a header that
            # under-declares size cannot yield more bytes than declared — checking the
            # declared size is sufficient against decompression bombs.
            if info.file_size > MAX_ENTRY_UNCOMPRESSED:
                raise CCXSecurityError(f"entry too large (zip bomb?): {name!r}")
            total += info.file_size
        if total > MAX_TOTAL_UNCOMPRESSED:
            raise CCXSecurityError(f"archive too large uncompressed (zip bomb?): {total}")

    def names(self) -> list[str]:
        return list(self._names)

    def has(self, name: str) -> bool:
        return name in self._names

    def read(self, name: str) -> bytes:
        try:
            return self._zf.read(name)
        except KeyError as exc:
            raise CCXValidationError(f"missing entry: {name!r}") from exc
        except (zipfile.BadZipFile, zlib.error) as exc:
            raise CCXValidationError(f"corrupt entry {name!r}: {exc}") from exc

    def check_mimetype(self) -> None:
        """The first entry MUST be `mimetype` and contain the CCX media type."""
        if not self._names or self._names[0] != MIMETYPE_PATH:
            raise CCXValidationError(f"first archive entry must be {MIMETYPE_PATH!r}")
        if self._zf.getinfo(MIMETYPE_PATH).compress_type != zipfile.ZIP_STORED:
            raise CCXValidationError(
                f"{MIMETYPE_PATH!r} must be stored uncompressed (ZIP STORED)"
            )
        value = self.read(MIMETYPE_PATH).decode("ascii", "replace").strip()
        if value != MIMETYPE:
            raise CCXValidationError(f"mimetype must be {MIMETYPE!r}, got {value!r}")
