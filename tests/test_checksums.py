from ccx import checksums


def test_sha256_of_empty_bytes_known_vector():
    # Well-known base64 of SHA-256("")
    assert checksums.sha256_b64(b"") == "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="


def test_compute_and_verify_roundtrip():
    data = b"hello ccx"
    s256, s512 = checksums.compute(data)
    assert checksums.verify(data, s256, s512) is True


def test_verify_fails_on_mismatch():
    s256, s512 = checksums.compute(b"original")
    assert checksums.verify(b"tampered", s256, s512) is False
