import json

from docreview360.log_hash_chain import batch_hash_logs
from docreview360.logs import clear_logs, export_logs, log_event

from services.log_chain_verifier import verify_log_chain


def test_verify_log_chain(tmp_path) -> None:
    clear_logs()
    log_event("alpha", user_id="u1")
    key = "chain.json"
    batch_hash_logs(batch_size=1, bucket=tmp_path, key=key, user_id="system")
    assert verify_log_chain(batch_size=1, bucket=tmp_path, key=key, user_id="system")
    logs = export_logs("system", log_access=False)
    assert all(entry.action != "log_chain_integrity_failure" for entry in logs)

    path = tmp_path / key
    chain = json.loads(path.read_text())
    chain[0] = "0" * 64
    path.write_text(json.dumps(chain))
    assert not verify_log_chain(batch_size=1, bucket=tmp_path, key=key, user_id="system")
    logs = export_logs("system", log_access=False)
    assert logs[-1].action == "log_chain_integrity_failure"
