def test_package_imports():
    import ccx

    assert isinstance(ccx.__version__, str) and ccx.__version__
