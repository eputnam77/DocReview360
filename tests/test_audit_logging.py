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


def test_audit_hmac_key_rotation(tmp_path, monkeypatch):
    """Entries signed with the old key remain verifiable after key rotation."""
    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    audit.clear_audit_log()

    old_key = "old-hmac-secret"
    new_key = "new-hmac-secret"

    # Write an entry with the OLD key.
    monkeypatch.setattr(audit, "_AUDIT_HMAC_KEY", old_key)
    monkeypatch.setattr(audit, "_AUDIT_HMAC_KEY_PREVIOUS", None)
    entry_old = audit.log_audit_event("doc", "before_rotation", actor="alice")

    # Rotate: primary → new key, previous → old key.
    monkeypatch.setattr(audit, "_AUDIT_HMAC_KEY", new_key)
    monkeypatch.setattr(audit, "_AUDIT_HMAC_KEY_PREVIOUS", old_key)

    # Write an entry with the NEW key.
    entry_new = audit.log_audit_event("doc", "after_rotation", actor="bob")

    # Both entries should be retrievable without integrity errors.
    events = audit.get_audit_log("doc")
    ids = {e.id for e in events}
    assert entry_old.id in ids, "Old entry should still be readable after rotation"
    assert entry_new.id in ids, "New entry should be readable with the new key"

    # Verify individual entry lookup also works for the old entry.
    fetched = audit.get_audit_entry(entry_old.id)
    assert fetched is not None and fetched.event == "before_rotation"


def test_audit_hmac_mismatch_raises(tmp_path, monkeypatch):
    """An entry with a tampered hash raises AuditLogIntegrityError."""
    import json

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    audit.clear_audit_log()

    key = "test-hmac-key"
    monkeypatch.setattr(audit, "_AUDIT_HMAC_KEY", key)
    monkeypatch.setattr(audit, "_AUDIT_HMAC_KEY_PREVIOUS", None)
    audit.log_audit_event("doc", "tampered")

    # Corrupt the hash field in the log file.
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    corrupted = []
    for line in lines:
        data = json.loads(line)
        data["hash"] = "deadbeef" * 8
        corrupted.append(json.dumps(data))
    log_path.write_text("\n".join(corrupted) + "\n", encoding="utf-8")

    import pytest
    with pytest.raises(audit.AuditLogIntegrityError):
        audit.get_audit_log("doc")


def test_purge_mid_crash_original_intact(tmp_path, monkeypatch):
    """Simulates a crash during os.replace and verifies the original log is preserved.

    The atomic write pattern writes to a .tmp file then calls os.replace().
    If os.replace() is interrupted, the original log must remain untouched.
    """
    import os

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    audit.clear_audit_log()

    from datetime import timedelta
    past = datetime.now(timezone.utc) - timedelta(days=2)
    entry = audit.log_audit_event("doc", "old_event", actor="alice", verified_at=past)
    recent = audit.log_audit_event("doc", "recent_event", actor="bob")

    original_content = log_path.read_text(encoding="utf-8")

    # Monkeypatch os.replace to simulate a crash after the .tmp file is written
    # but before the rename completes.
    def _crash_replace(src: str, dst: str) -> None:
        raise OSError("Simulated crash during os.replace")

    monkeypatch.setattr(os, "replace", _crash_replace)

    import pytest
    with pytest.raises(OSError, match="Simulated crash"):
        audit.purge_audit_logs(retention_days=1)

    # The original log must be intact — no data lost.
    assert log_path.read_text(encoding="utf-8") == original_content

    # The .tmp file should have been cleaned up by the except block.
    tmp_path_file = log_path.with_suffix(".tmp")
    assert not tmp_path_file.exists(), ".tmp file should be cleaned up on failure"


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
