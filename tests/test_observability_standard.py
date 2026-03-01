import json
import logging

from fastapi.testclient import TestClient

from docreview360.api import app, reset_rate_limiters_for_testing
from docreview360.logs import TRACE_ID, clear_logs, log_event, query_logs


def test_log_event_redacts_sensitive_fields() -> None:
    clear_logs()
    entry = log_event(
        "security_event",
        password="super-secret",
        metadata={"access_token": "abc123", "safe": "ok"},
    )

    assert entry.details["password"] == "[REDACTED]"
    assert entry.details["metadata"]["access_token"] == "[REDACTED]"
    assert entry.details["metadata"]["safe"] == "ok"


def test_log_event_normalizes_severity_and_error_taxonomy() -> None:
    clear_logs()
    entry = log_event("provider_failure", severity="ERROR", error_code="bad-value")

    assert entry.severity == "error"
    assert entry.details["error_code"] == "system_error"


def test_log_event_emits_structured_json_in_production(monkeypatch, caplog) -> None:
    clear_logs()
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    caplog.set_level(logging.INFO, logger="docreview360.audit")

    log_event("structured_probe", user_id="alice", entity_id="doc-1")

    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "docreview360.audit"
    ]
    assert messages

    payload = json.loads(messages[-1])
    assert payload["action"] == "structured_probe"
    assert payload["severity"] == "info"
    assert payload["entity_id"] == "doc-1"


def test_correlation_id_header_is_propagated() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"X-Correlation-ID": "cid-health-001"})

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "cid-health-001"
    assert TRACE_ID.get(None) is None


def test_correlation_id_is_attached_to_login_log_event() -> None:
    clear_logs()
    reset_rate_limiters_for_testing()
    client = TestClient(app)

    response = client.post(
        "/token",
        data={"username": "alice", "password": "password"},
        headers={"X-Correlation-ID": "cid-login-001"},
    )

    assert response.status_code == 200
    login_logs = query_logs(action="login", user_id="alice")
    assert login_logs
    assert login_logs[-1].details.get("trace_id") == "cid-login-001"


