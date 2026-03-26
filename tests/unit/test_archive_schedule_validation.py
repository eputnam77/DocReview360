from datetime import timedelta

import pytest
from docreview360 import archive
from docreview360.celery_app import app


def test_schedule_archive_purge_invalid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        archive,
        "load_settings",
        lambda: {"archive": {"retention_days": 0, "purge_interval_minutes": -5}},
    )
    original_schedule = app.conf.get("beat_schedule")
    app.conf.beat_schedule = {}
    try:
        archive.schedule_archive_purge()
        entry = app.conf.beat_schedule["purge_archives"]
        assert entry["args"] == (archive.ARCHIVE_RETENTION_DAYS,)
        assert entry["schedule"] == timedelta(minutes=60 * 24)
    finally:
        app.conf.beat_schedule = original_schedule
