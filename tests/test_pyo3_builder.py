import zipfile

from docreview360.pyo3_builder import build_stub_wheel


def test_build_stub_wheel(tmp_path):
    path = tmp_path / "stub.whl"
    wheel = build_stub_wheel(path, package="pkg", version="1.2")
    assert wheel == path
    with zipfile.ZipFile(wheel) as zf:
        assert "pkg-1.2.dist-info/WHEEL" in zf.namelist()
        assert zf.read("pkg/__init__.py") == b""
