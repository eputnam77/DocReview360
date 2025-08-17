from fastapi.testclient import TestClient

from docreview360 import project_preferences
from docreview360.api import app


def test_project_preferences_persist(tmp_path, monkeypatch) -> None:
    path = tmp_path / "settings.yaml"
    monkeypatch.setattr(project_preferences, "SETTINGS_FILE", path)

    client = TestClient(app)
    project_id = "demo-project"
    resp = client.put(
        f"/projects/{project_id}/preferences",
        json={"lint": True, "collab": True, "watermark_text": "Secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["lint"] is True

    client2 = TestClient(app)
    resp2 = client2.get(f"/projects/{project_id}/preferences")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["lint"] is True
    assert data["collab"] is True
    assert data["watermark_text"] == "Secret"
