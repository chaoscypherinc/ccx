"""Exception hierarchy for the CCX reader."""

from __future__ import annotations


class CCXError(Exception):
    """Base class for all CCX reader errors."""


class CCXValidationError(CCXError):
    """The package is structurally or schematically invalid."""


class CCXIntegrityError(CCXError):
    """A checksum or signature did not verify.

    Reserved for strict / signature verification (a later milestone). The Core
    ``validate()`` reports checksum mismatches as entries in
    ``ValidationReport.errors`` rather than raising, so it does not raise this yet.
    """


class CCXSecurityError(CCXError):
    """The package tried to do something unsafe (zip bomb, traversal, network)."""
