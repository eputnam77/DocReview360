import json
from pathlib import Path

from docreview360.log_hash_chain import batch_hash_logs
from docreview360.logs import clear_logs, export_logs, log_event
from docreview360.notifications import sent_emails
from services.log_chain_verifier import verify_log_chain


def test_verify_log_chain(tmp_path: Path) -> None:
    clear_logs()
    sent_emails.clear()
    log_event("alpha", user_id="u1")
    key = "chain.json"
    batch_hash_logs(batch_size=1, bucket=tmp_path, key=key, user_id="system")
    assert verify_log_chain(
        batch_size=1,
        bucket=tmp_path,
        key=key,
        user_id="system",
        alert_email="admin@example.com",
    )
    logs = export_logs("system", log_access=False)
    assert logs[-1].action == "log_chain_verification"
    assert logs[-1].details.get("result") == "success"
    assert sent_emails == []

    path = tmp_path / key
    chain = json.loads(path.read_text())
    chain[0] = "0" * 64
    path.write_text(json.dumps(chain))
    assert not verify_log_chain(
        batch_size=1,
        bucket=tmp_path,
        key=key,
        user_id="system",
        alert_email="admin@example.com",
    )
    logs = export_logs("system", log_access=False)
    assert logs[-2].action == "log_chain_verification"
    assert logs[-2].details.get("result") == "mismatch"
    assert logs[-1].action == "log_chain_integrity_failure"
    assert sent_emails[-1]["to"] == "admin@example.com"
