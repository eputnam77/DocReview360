import json

from docreview360.log_hash_chain import batch_hash_logs, verify_hash_chain
from docreview360.logs import clear_logs, log_event


def test_log_hash_chain(tmp_path) -> None:
    clear_logs()
    log_event("alpha", user_id="u1")
    log_event("beta", user_id="u2")
    key = "chain.json"
    batch_hash_logs(batch_size=1, bucket=tmp_path, key=key)
    assert verify_hash_chain(batch_size=1, bucket=tmp_path, key=key)

    path = tmp_path / key
    chain = json.loads(path.read_text())
    chain[0] = "0" * 64
    path.write_text(json.dumps(chain))
    assert not verify_hash_chain(batch_size=1, bucket=tmp_path, key=key)
