from datetime import timedelta

import pytest

import services.signature_verifier as signature_verifier
from docreview360.celery_app import app
from services.signature_verifier import schedule_signature_verification


def test_schedule_signature_verification_defaults_invalid_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        signature_verifier,
        "load_settings",
        lambda: {"signature_verification": {"interval_minutes": "bad", "scope": " "}},
    )
    monkeypatch.setattr(signature_verifier, "schedule_audit_log_purge", lambda: None)
    monkeypatch.setattr(signature_verifier, "schedule_audit_log_hashing", lambda: None)
    monkeypatch.setattr(signature_verifier, "schedule_archive_purge", lambda: None)

    app.conf.beat_schedule = {}
    schedule_signature_verification()

    entry = app.conf.beat_schedule["signature_verification"]
    assert entry["schedule"] == timedelta(minutes=60)
    assert entry["args"] == ("approved",)
