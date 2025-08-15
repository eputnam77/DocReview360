from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.logs import log_event


def test_log_websocket() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as ws:
        log_event("test", user_id="alice")
        data = ws.receive_json()
        assert data["action"] == "test"
        assert data["user_id"] == "alice"
