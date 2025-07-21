from pathlib import Path
from zipfile import ZipFile

from docreview360.pyo3_builder import build_stub_wheel


def test_build_stub_wheel(tmp_path: Path) -> None:
    wheel = build_stub_wheel(tmp_path / "pkg.whl")
    assert wheel.exists()

    with ZipFile(wheel) as zf:
        names = zf.namelist()
        assert any(name.endswith(".dist-info/WHEEL") for name in names)
        assert any(name.endswith(".dist-info/METADATA") for name in names)
