import json

import pytest
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


def test_log_hash_chain_idempotent(tmp_path) -> None:
    clear_logs()
    log_event("alpha", user_id="u1")
    key = "chain.json"
    first = batch_hash_logs(batch_size=1, bucket=tmp_path, key=key)
    second = batch_hash_logs(batch_size=1, bucket=tmp_path, key=key)
    assert first == second


@pytest.mark.parametrize("batch_size", [0, -1])
def test_log_hash_chain_rejects_non_positive_batch_size(batch_size) -> None:
    with pytest.raises(ValueError, match="batch_size must be positive"):
        batch_hash_logs(batch_size=batch_size, bucket="tmp", key="chain.json")
    with pytest.raises(ValueError, match="batch_size must be positive"):
        verify_hash_chain(batch_size=batch_size, bucket="tmp", key="chain.json")


def test_log_hash_chain_rejects_non_integer_batch_size() -> None:
    with pytest.raises(TypeError, match="batch_size must be an integer"):
        batch_hash_logs(batch_size="10", bucket="tmp", key="chain.json")
    with pytest.raises(TypeError, match="batch_size must be an integer"):
        verify_hash_chain(batch_size="10", bucket="tmp", key="chain.json")
