from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from docreview360 import settings_manager
from docreview360.api import app
from docreview360.integrations.signature import base, documenso


def test_signature_provider_persistence_and_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Settings store both providers and fallback works."""

    path = tmp_path / "settings.yaml"
    orig_load = settings_manager.load_settings
    orig_update = settings_manager.update_setting

    def _load(path: Path = path) -> Dict[str, Any]:
        return orig_load(path)

    def _update(key: str, value: Any, path: Path = path) -> None:
        orig_update(key, value, path)

    monkeypatch.setattr(settings_manager, "load_settings", _load)
    monkeypatch.setattr(settings_manager, "update_setting", _update)
    monkeypatch.setattr(base, "load_settings", _load)
    monkeypatch.setattr("docreview360.api.update_setting", _update)
    monkeypatch.delenv("SIGNATURE_PROVIDER", raising=False)
    monkeypatch.delenv("SIGNATURE_PROVIDER_PRIMARY", raising=False)
    monkeypatch.delenv("SIGNATURE_PROVIDER_FALLBACK", raising=False)

    client = TestClient(app)
    resp = client.put(
        "/signature-provider",
        json={"primary": "missing", "fallback": "documenso"},
    )
    assert resp.status_code == 200

    data = orig_load(path)
    assert data["signature_provider_primary"] == "missing"
    assert data["signature_provider_fallback"] == "documenso"

    base.providers.clear()
    base.register_provider(documenso.DocumensoProvider())
    provider = base.get_provider()
    assert provider.name == "documenso"

    get_resp = client.get("/signature-provider")
    assert get_resp.json() == {"primary": "missing", "fallback": "documenso"}
