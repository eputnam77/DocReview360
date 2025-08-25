from pathlib import Path
from datetime import timedelta
import types
import pytest

from docreview360 import settings_manager


def test_load_settings_non_mapping(tmp_path: Path) -> None:
    file = tmp_path / "cfg.yaml"
    file.write_text("- just\n- a\n- list\n")
    with pytest.raises(ValueError):
        settings_manager.load_settings(file)


def test_update_setting_and_vault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = []
    monkeypatch.setattr(settings_manager, "configure_vault", lambda cfg: calls.append(cfg))
    monkeypatch.setattr(settings_manager, "record_task_completion", lambda tid: calls.append(tid))
    path = tmp_path / "set.yaml"
    settings_manager.update_setting("vault", {"url": "u"}, path)
    assert calls[0] == {"url": "u"}
    assert calls[1] == 142
    assert settings_manager.load_settings(path)["vault"] == {"url": "u"}


def test_load_providers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # stub entry points
    class DummyEP:
        def __init__(self, obj=None, exc=False, name="prov"):
            self._obj = obj
            self._exc = exc
            self.name = name

        def load(self):
            if self._exc:
                raise RuntimeError("boom")
            return self._obj

    eps = [DummyEP(object()), DummyEP(exc=True, name="bad")]
    entry_pts = types.SimpleNamespace(select=lambda group: eps)
    monkeypatch.setattr(settings_manager.metadata, "entry_points", lambda: entry_pts)

    regs = []
    monkeypatch.setattr(
        "docreview360.integrations.registry.register_provider",
        lambda provider, name=None: regs.append((provider, name)),
    )

    monkeypatch.setattr(settings_manager, "load_settings", lambda: {"provider_modules": ["m1", "m2"]})

    imported = []

    def import_stub(name):
        imported.append(name)
        if name == "m2":
            raise RuntimeError("fail")

    monkeypatch.setattr(settings_manager, "import_module", import_stub)

    settings_manager.load_providers()

    assert regs[0][1] == "prov"  # default name fallback
    assert imported == ["m1", "m2"]
