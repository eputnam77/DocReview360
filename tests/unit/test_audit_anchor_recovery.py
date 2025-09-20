from __future__ import annotations

from pathlib import Path

import pytest

from docreview360 import audit


def test_hash_new_log_segments_resets_future_anchor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Anchors pointing past the end of the log should be clamped."""

    log_path = tmp_path / "audit.log"
    anchor_path = tmp_path / "audit.anchor"
    log_path.write_text("entry-1\nentry-2\nentry-3\n", encoding="utf-8")
    anchor_path.write_text("10", encoding="utf-8")

    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "_AUDIT_ANCHOR_PATH", anchor_path)

    uploads: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _record_upload(*args: object, **kwargs: object) -> None:
        uploads.append((args, kwargs))

    monkeypatch.setattr(audit, "upload_file", _record_upload)

    processed = audit.hash_new_log_segments(segment_size=2)

    assert processed == 0
    assert anchor_path.read_text(encoding="utf-8") == "3"
    assert uploads == []
