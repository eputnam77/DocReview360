from docreview360 import audit


def test_hash_new_log_segments_handles_negative_anchor(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    log_path.write_text("a\n" "b\n" "c\n")
    anchor_path = tmp_path / "audit.anchor"
    anchor_path.write_text("-5")

    calls = []

    def fake_upload(bucket, key, data, append_only=True, retention_days=1):
        calls.append((bucket, key, data, append_only, retention_days))
        return bucket / key

    monkeypatch.setattr(audit, "upload_file", fake_upload)
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(audit, "_AUDIT_ANCHOR_PATH", anchor_path)

    count = audit.hash_new_log_segments(bucket=tmp_path, segment_size=1)

    assert count == 3
    assert anchor_path.read_text() == "3"
    assert len(calls) == 3
