"""Coverage for audit retention and hashing schedule defaults."""

from __future__ import annotations

from datetime import timedelta

from docreview360 import audit
from docreview360.celery_app import app


def test_purge_audit_logs_clamps_negative_retention(monkeypatch, tmp_path) -> None:
    """Negative retention settings should fall back to defaults."""
    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "load_settings", lambda: {"audit_log": {"retention_days": -5}})

    audit.log_audit_event("doc-1", "created")
    removed = audit.purge_audit_logs()

    assert removed == 0
    assert log_path.exists()


def test_schedule_audit_log_hashing_invalid_settings(monkeypatch) -> None:
    """Hashing schedules should tolerate malformed configuration values."""
    monkeypatch.setattr(
        audit,
        "load_settings",
        lambda: {
            "audit_log": {
                "hash_interval_minutes": "not-a-number",
                "hash_bucket": "   ",
                "hash_prefix": None,
                "hash_segment_size": 0,
                "hash_retention_days": -1,
            }
        },
    )
    original_schedule = dict(app.conf.get("beat_schedule", {}))
    try:
        audit.schedule_audit_log_hashing()
        schedule = app.conf.beat_schedule["hash_audit_log"]
        assert schedule["schedule"] == timedelta(minutes=60)
        assert schedule["kwargs"]["bucket"] == "tamper_proof_store"
        assert schedule["kwargs"]["prefix"] == "audit_anchors"
        assert schedule["kwargs"]["segment_size"] == 100
        assert schedule["kwargs"]["retention_days"] == 365
    finally:
        app.conf.beat_schedule = original_schedule
