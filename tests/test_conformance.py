import ccx
from ccx import open_package
from tests import fixtures


def test_public_api_surface():
    expected = {
        "CCXError",
        "CCXValidationError",
        "CCXIntegrityError",
        "CCXSecurityError",
        "Manifest",
        "GraphEntry",
        "AssetEntry",
        "load_manifest",
        "CCXPackage",
        "ValidationReport",
        "open_package",
        "PackageBuilder",
        "write_package",
        "generate_ed25519_keypair",
        "__version__",
    }
    for symbol in expected:
        assert hasattr(ccx, symbol), symbol
        assert symbol in ccx.__all__, symbol
    assert set(ccx.__all__) == expected


def test_valid_fixture_passes_core():
    assert open_package(fixtures.core_minimal()).validate().ok is True


def test_all_invalid_fixtures_are_rejected():
    # Each invalid fixture must EITHER fail to open OR fail validation.
    builders = list(fixtures.INVALID_BUILDERS.values())
    for builder in builders:
        data = builder()
        try:
            pkg = open_package(data)
        except ccx.CCXError:
            continue  # rejected at open time — acceptable
        report = pkg.validate()
        # some fixtures fail at open, some at validate, some only when the dataset loads
        if report.ok:
            try:
                pkg.dataset()
            except ccx.CCXError:
                continue
            raise AssertionError(f"{builder.__name__} was not rejected")


def test_remote_context_rejected_by_validate():
    report = open_package(fixtures.remote_context()).validate()
    assert report.ok is False
    assert any("context" in e for e in report.errors)


def test_writer_symbols_exported():
    assert hasattr(ccx, "PackageBuilder")
    assert hasattr(ccx, "write_package")
    assert "PackageBuilder" in ccx.__all__
    assert "write_package" in ccx.__all__
