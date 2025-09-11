import pytest

from docreview360.plugin_marketplace import install_plugin


def test_install_plugin_non_string(monkeypatch):
    # Avoid executing pip
    monkeypatch.setattr("subprocess.check_call", lambda *a, **k: (_ for _ in ()).throw(RuntimeError))
    with pytest.raises(TypeError):
        install_plugin(123)  # type: ignore[arg-type]
