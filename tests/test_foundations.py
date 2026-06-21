import pytest

from ccx import errors
from ccx import constants


def test_exception_hierarchy():
    assert issubclass(errors.CCXValidationError, errors.CCXError)
    assert issubclass(errors.CCXIntegrityError, errors.CCXError)
    assert issubclass(errors.CCXSecurityError, errors.CCXError)


def test_constants_present():
    assert constants.MIMETYPE == "application/vnd.ccx+zip"
    assert constants.CCX_VERSION == "3.0"
    assert constants.MIMETYPE_PATH == "mimetype"
    assert constants.MANIFEST_PATH == "manifest.json"
    assert constants.CONTEXT_PATH == "context.jsonld"
    assert constants.MAX_ENTRY_UNCOMPRESSED > 0
