from __future__ import annotations

from docreview360 import audit


def test_audit_log_lifecycle(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "audit.log"
    anchor_path = tmp_path / "audit.log.anchor"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "_AUDIT_ANCHOR_PATH", anchor_path)

    from datetime import datetime, timedelta, timezone

    old_time = datetime.now(timezone.utc) - timedelta(days=2)
    entry = audit.log_audit_event("doc1", "created", actor="alice", verified_at=old_time)
    events = audit.get_audit_log("doc1")
    assert events[0].id == entry.id
    assert audit.get_audit_entry(entry.id) is not None

    # Purge removes existing entry when older than retention
    assert audit.purge_audit_logs(retention_days=1) == 1

    # Hashing processes new segments and updates anchor
    audit.log_audit_event("doc1", "updated", actor="alice")
    count = audit.hash_new_log_segments(bucket=str(tmp_path), prefix="anchors", segment_size=1)
    assert count == 1
