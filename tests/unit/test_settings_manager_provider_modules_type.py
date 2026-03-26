import pytest
from docreview360 import settings_manager


def test_load_providers_rejects_non_list_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_manager, "load_settings", lambda: {"provider_modules": "oops"})
    with pytest.raises(ValueError, match="provider_modules must be a list"):
        settings_manager.load_providers()
