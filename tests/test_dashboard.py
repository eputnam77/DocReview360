from fastapi.testclient import TestClient

from docuflow import search
from docuflow.api import app


def test_dashboard_websocket() -> None:
    search.projects.clear()
    search.add_project(search.ProjectModel(id="ws1", name="WebSocket Demo"))
    client = TestClient(app)
    with client.websocket_connect("/ws/dashboard") as ws:
        data = ws.receive_json()
        ids = {entry["id"] for entry in data}
        assert "ws1" in ids
