from datetime import datetime, timedelta, timezone

from docreview360 import audit


def test_audit_log_roundtrip(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    audit.clear_audit_log()
    past = datetime.now(timezone.utc) - timedelta(days=2)
    entry = audit.log_audit_event("doc", "created", actor="alice", verified_at=past)
    logs = audit.get_audit_log("doc")
    assert logs and logs[0].id == entry.id
    fetched = audit.get_audit_entry(entry.id)
    assert fetched and fetched.event == "created"
    # purge everything by setting retention to 0 days
    removed = audit.purge_audit_logs(1)
    assert removed >= 1


def test_hash_new_log_segments(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    log_path.write_text("a\n" * 4)
    anchor_path = tmp_path / "audit.anchor"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "_AUDIT_ANCHOR_PATH", anchor_path)
    bucket = tmp_path / "bucket"
    count = audit.hash_new_log_segments(bucket=bucket, segment_size=2, retention_days=1)
    assert count == 2
    assert (bucket / "audit_anchors/segment_0.sha256").exists()
