import json
from datetime import datetime, timedelta, timezone

import pytest

import docreview360.audit as audit
import docreview360.integrity as integrity
import docreview360.logs as logs


@pytest.fixture
def corruption_environment(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    anchor_path = tmp_path / "audit.anchor"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "_AUDIT_ANCHOR_PATH", anchor_path)

    events: list[tuple[str, dict[str, object]]] = []

    def fake_log_event(action: str, **context: object) -> None:
        events.append((action, context))

    monkeypatch.setattr(logs, "log_event", fake_log_event)

    calls = {"verify": 0, "hash": 0}

    class DummyVerifyTask:
        def delay(self) -> None:
            calls["verify"] += 1

    monkeypatch.setattr(integrity, "verify_integrity", DummyVerifyTask())

    def fake_hash_new_log_segments(*args, **kwargs):
        calls["hash"] += 1
        return 0

    monkeypatch.setattr(audit, "hash_new_log_segments", fake_hash_new_log_segments)

    return log_path, calls, events


def test_get_audit_log_alerts_on_malformed_entry(corruption_environment):
    log_path, calls, events = corruption_environment
    log_path.write_text("{not json}\n", encoding="utf-8")

    with pytest.raises(audit.AuditLogIntegrityError) as excinfo:
        audit.get_audit_log("doc-123")

    assert excinfo.value.reason == "malformed_json"
    assert any(action == "audit_log_corruption_detected" for action, _ in events)
    assert calls["verify"] == 1
    assert calls["hash"] == 1


def test_get_audit_log_alerts_on_hash_mismatch(corruption_environment):
    log_path, calls, events = corruption_environment
    now = datetime.now(timezone.utc)
    data = {
        "id": "entry-1",
        "event": "signed",
        "document_id": "doc-456",
        "status": "ok",
        "hash": "tampered",
        "certificate_url": None,
        "verified_at": now.isoformat(),
        "verifier": "ops",
        "context": {},
    }
    log_path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    with pytest.raises(audit.AuditLogIntegrityError) as excinfo:
        audit.get_audit_log("doc-456", secret="secret-key")

    assert excinfo.value.reason == "hash_mismatch"
    assert any(
        action == "audit_log_corruption_detected" and event.get("document") == "doc-456"
        for action, event in events
    )
    assert calls["verify"] == 1
    assert calls["hash"] == 1


def test_purge_respects_settings(monkeypatch, tmp_path):
    log_path = tmp_path / "audit.log"
    anchor_path = tmp_path / "audit.anchor"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "_AUDIT_ANCHOR_PATH", anchor_path)

    old = datetime.now(timezone.utc) - timedelta(days=11)
    recent = datetime.now(timezone.utc)
    entries = [
        {
            "id": "old",
            "event": "created",
            "document_id": "doc-1",
            "status": "ok",
            "hash": "",  # Purge logic does not validate the hash
            "certificate_url": None,
            "verified_at": old.isoformat(),
            "verifier": None,
            "context": {},
        },
        {
            "id": "fresh",
            "event": "created",
            "document_id": "doc-1",
            "status": "ok",
            "hash": "",
            "certificate_url": None,
            "verified_at": recent.isoformat(),
            "verifier": None,
            "context": {},
        },
    ]
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")

    monkeypatch.setattr(
        audit,
        "load_settings",
        lambda: {"audit_log": {"retention_days": 10, "purge_interval_minutes": 5}},
    )

    removed = audit.purge_audit_logs()

    assert removed == 1
    remaining = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(remaining) == 1
    assert json.loads(remaining[0])["id"] == "fresh"
