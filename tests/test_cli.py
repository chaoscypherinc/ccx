import json as _json
from pathlib import Path

from ccx.cli import main
from tests import fixtures


def _write(tmp_path: Path, data: bytes) -> str:
    p = tmp_path / "pkg.ccx"
    p.write_bytes(data)
    return str(p)


def test_inspect_valid(tmp_path, capsys):
    code = main(["inspect", _write(tmp_path, fixtures.core_minimal())])
    out = capsys.readouterr().out
    assert code == 0
    assert "demo/people" in out
    assert "knowledge" in out


def test_validate_valid(tmp_path, capsys):
    code = main(["validate", _write(tmp_path, fixtures.core_minimal())])
    out = capsys.readouterr().out
    assert code == 0
    assert "VALID" in out


def test_validate_bad_checksum_fails(tmp_path, capsys):
    code = main(["validate", _write(tmp_path, fixtures.bad_checksum())])
    err = capsys.readouterr().err
    assert code == 1
    assert "checksum" in err or "INVALID" in err


def test_validate_unopenable_returns_1(tmp_path, capsys):
    code = main(["validate", _write(tmp_path, b"not a zip")])
    assert code == 1


def test_inspect_open_error_returns_2(tmp_path, capsys):
    code = main(["inspect", _write(tmp_path, b"not a zip")])
    err = capsys.readouterr().err
    assert code == 2
    assert "error" in err


def test_validate_valid_but_warns(tmp_path, capsys):
    code = main(["validate", _write(tmp_path, fixtures.valid_without_license())])
    captured = capsys.readouterr()
    assert code == 0
    assert "VALID" in captured.out
    assert "warning" in captured.err
    assert "license" in captured.err


def _make_src_dir(tmp_path):
    src = tmp_path / "src"
    (src / "graphs").mkdir(parents=True)
    (src / "assets").mkdir(parents=True)
    (src / "manifest.json").write_text(_json.dumps({
        "name": "demo/people", "package_version": "1.0.0", "license": "CC-BY-4.0",
        "base_iri": "urn:ccx:demo:",
    }))
    (src / "knowledge.jsonld").write_text(_json.dumps({
        "@context": {"ccx": "https://w3id.org/ccx/", "schema": "https://schema.org/",
                     "name": "schema:name", "Person": "schema:Person"},
        "@graph": [{"@id": "urn:ccx:demo:alice", "@type": "Person", "name": "Alice Smith"}],
    }))
    (src / "graphs" / "acme.notes.jsonld").write_text(_json.dumps({
        "@context": {"acme": "https://acme.example/ns#"}, "@graph": []}))
    (src / "assets" / "p.png").write_bytes(b"\x89PNG\r\n\x1a\nx")
    return src


def test_pack_builds_valid_package(tmp_path, capsys):
    from ccx import open_package

    src = _make_src_dir(tmp_path)
    out = tmp_path / "out.ccx"
    code = main(["pack", str(src), "-o", str(out)])
    assert code == 0
    pkg = open_package(str(out))
    assert pkg.validate().ok is True
    paths = {g.path for g in pkg.manifest.graphs}
    assert {"knowledge.jsonld", "graphs/acme.notes.jsonld"} <= paths
    assert len(pkg.manifest.assets) == 1


def test_pack_missing_dir_fails(tmp_path):
    code = main(["pack", str(tmp_path / "nope"), "-o", str(tmp_path / "o.ccx")])
    assert code != 0


def test_pack_bad_graph_filename_fails(tmp_path):
    src = _make_src_dir(tmp_path)
    (src / "graphs" / "noseparator.jsonld").write_text(_json.dumps({"@graph": []}))
    code = main(["pack", str(src), "-o", str(tmp_path / "o.ccx")])
    assert code != 0
