from pathlib import Path

from docreview360.pyo3_builder import build_stub_wheel


def test_build_stub_wheel(tmp_path: Path) -> None:
    wheel = build_stub_wheel(tmp_path / "pkg.whl")
    assert wheel.exists()
    assert wheel.read_text() == "wheel"
