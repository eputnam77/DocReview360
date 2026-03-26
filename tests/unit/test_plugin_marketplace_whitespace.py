import pytest
from docreview360.plugin_marketplace import install_plugin


def test_install_plugin_rejects_whitespace_name(monkeypatch):
    # Prevent actual pip invocation if the validation fails unexpectedly
    monkeypatch.setattr(
        "subprocess.check_call", lambda *a, **k: (_ for _ in ()).throw(RuntimeError)
    )
    with pytest.raises(ValueError) as exc:
        install_plugin("   ")
    assert "name is required" in str(exc.value)
