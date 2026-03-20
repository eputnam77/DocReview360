from datetime import timedelta

import pytest
from docreview360 import auth, search
from docreview360.api import app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture(autouse=True)
def _isolated_auth(tmp_path):
    auth.configure_user_repository(tmp_path / "users.db")
    for username in ("alice", "bob"):
        password = auth.DEMO_USER_DEFAULTS[username]["password"]
        otp_secret = auth.DEMO_USER_DEFAULTS[username].get("otp_secret")
        try:
            auth.USER_REPOSITORY.create_user(username, password, otp_secret=otp_secret)
        except Exception:
            pass



def test_dashboard_websocket_requires_valid_jwt_and_scopes_to_token_user() -> None:
    search.projects.clear()
    search.add_project(search.ProjectModel(id="ws-alice", name="Alice Project", user="alice"))
    search.add_project(search.ProjectModel(id="ws-bob", name="Bob Project", user="bob"))
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/dashboard?user=bob"):
            pass
    assert excinfo.value.code == 1008

    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=5))
    with client.websocket_connect(f"/ws/dashboard?token={token}&user=alice") as ws:
        data = ws.receive_json()
        ids = {entry["id"] for entry in data}
        assert ids == {"ws-alice"}
        first = data[0]
        assert "routing_latency" in first
        assert "critic_models" in first

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(f"/ws/dashboard?token={token}&user=bob"):
            pass
    assert excinfo.value.code == 1008
