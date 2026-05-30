from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from docreview360 import api as api_mod
from docreview360 import auth
from docreview360 import config as conf_mod
from docreview360.config import Config, load_with_defaults
from docreview360.search import ProjectModel


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_load_with_defaults_uses_runtime_config_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "docreview360.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)

    loaded = load_with_defaults()
    assert loaded.editor == "tiptap"

    Config(database="sqlite", editor="tiptap", cms="none", auth="oidc").save(cfg_path)
    loaded_after_write = load_with_defaults()
    assert loaded_after_write.editor == "tiptap"


def test_project_model_exposes_editor_from_runtime_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg_path = tmp_path / "docreview360.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    Config(database="sqlite", editor="tiptap", cms="none", auth="oidc").save(cfg_path)

    project = ProjectModel(id="proj-editor", name="Editor Config Project")
    assert project.model_dump(mode="json")["editor"] == "tiptap"


def test_project_endpoint_returns_configured_editor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg_path = tmp_path / "docreview360.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    Config(database="sqlite", editor="tiptap", cms="none", auth="oidc").save(cfg_path)

    client = TestClient(api_mod.app)
    create_resp = client.post(
        "/projects",
        headers=_alice_headers(),
        json={
            "name": f"Config-backed editor {uuid4().hex[:8]}",
            "user": "alice",
        },
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}", headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.json()["editor"] == "tiptap"
