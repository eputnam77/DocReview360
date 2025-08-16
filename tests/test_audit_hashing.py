import docreview360.audit as audit
from docreview360.audit import clear_audit_log, hash_new_log_segments, log_audit_event


def test_hash_new_log_segments(tmp_path, monkeypatch):
    bucket = tmp_path / "bucket"
    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "_AUDIT_ANCHOR_PATH", log_path.with_suffix(".anchor"))
    clear_audit_log()

    log_audit_event("doc1", "evt1")
    log_audit_event("doc2", "evt2")
    log_audit_event("doc3", "evt3")

    count = hash_new_log_segments(bucket=bucket, prefix="anchors", segment_size=2)
    assert count == 2
    assert (bucket / "anchors" / "segment_0.sha256").exists()
    assert (bucket / "anchors" / "segment_1.sha256").exists()

    count2 = hash_new_log_segments(bucket=bucket, prefix="anchors", segment_size=2)
    assert count2 == 0
