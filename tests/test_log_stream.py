import pytest
from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.api import ml as ml_module
from docreview360.logs import log_event
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _patch_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_user(*args, **kwargs) -> auth.User:
        return auth.User(username="alice", active=True)

    monkeypatch.setattr(auth, "get_current_user", fake_user)
    monkeypatch.setattr(rbac.auth, "get_current_user", fake_user)

    def _has_permission(*args, **kwargs) -> bool:
        return True

    monkeypatch.setattr(rbac, "has_permission", _has_permission)

    async def _allow_rate_limit(*args, **kwargs) -> auth.User:
        return auth.User(username="alice", active=True)

    monkeypatch.setitem(app.dependency_overrides, ml_module._enforce_rate_limit, _allow_rate_limit)


def test_log_websocket() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as ws:
        log_event("test", user_id="alice")
        data = ws.receive_json()
        assert data["action"] == "test"
        assert data["user_id"] == "alice"


def test_critic_output_log_stream() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as ws:

        def emit_event() -> None:
            log_event(
                "critic_output",
                critic="quality",
                document_id="log-test",
                score=0.87,
                model={"version": "q1", "sha256": "stub"},
            )

        emit_event()
        for _ in range(10):
            message = ws.receive_json()
            if message["action"] != "critic_output":
                emit_event()
                continue
            details = message.get("details", {})
            if details.get("critic") != "quality":
                emit_event()
                continue
            model = details.get("model", {}) or {}
            if model:
                assert model.get("version") == "q1"
                assert "sha256" in model
            break
        else:
            pytest.fail("critic_output event not received")
