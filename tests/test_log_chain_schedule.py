from datetime import timedelta

from docreview360.celery_app import app
from services import log_chain_verifier as lcv


def test_schedule_log_chain_verification(monkeypatch):
    """Ensure the schedule entry is created correctly."""
    monkeypatch.setattr(lcv, "load_settings", lambda: {})
    app.conf.beat_schedule = {}

    lcv.schedule_log_chain_verification()

    assert "log_chain_verification" in app.conf.beat_schedule
    entry = app.conf.beat_schedule["log_chain_verification"]
    assert entry["task"] == "docreview360.verify_log_chain"
    assert isinstance(entry["schedule"], timedelta)
    assert entry["kwargs"]["bucket"] == "tamper_proof_store"
    assert entry["kwargs"]["key"] == "log_chain.json"


def test_schedule_log_chain_verification_respects_missing_email(monkeypatch):
    """Explicit ``None`` should disable email alerts rather than use 'None'."""

    monkeypatch.setattr(
        lcv,
        "load_settings",
        lambda: {"log_chain_verification": {"alert_email": None}},
    )
    app.conf.beat_schedule = {}

    lcv.schedule_log_chain_verification()

    entry = app.conf.beat_schedule["log_chain_verification"]
    assert entry["kwargs"]["alert_email"] is None


def test_schedule_log_chain_verification_invalid_settings(monkeypatch):
    monkeypatch.setattr(
        lcv,
        "load_settings",
        lambda: {
            "log_chain_verification": {
                "interval_minutes": "nope",
                "batch_size": 0,
                "bucket": "   ",
                "key": None,
            }
        },
    )
    app.conf.beat_schedule = {}

    lcv.schedule_log_chain_verification()

    entry = app.conf.beat_schedule["log_chain_verification"]
    assert entry["kwargs"]["bucket"] == "tamper_proof_store"
    assert entry["kwargs"]["key"] == "log_chain.json"
    assert entry["kwargs"]["batch_size"] == 100
