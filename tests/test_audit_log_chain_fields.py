import hashlib
import json

from docreview360.logs import clear_logs, log_event


def test_log_entry_chain_fields() -> None:
    clear_logs()
    first = log_event("alpha", user_id="u1", document_hash="hash1", provider_response={"p": 1})
    second = log_event("beta", user_id="u2")
    assert len(first.hash) == 64
    assert second.prev_hash == first.hash
    data = {
        "id": second.id,
        "timestamp": second.timestamp.isoformat(),
        "user_id": second.user_id,
        "action": second.action,
        "entity_type": second.entity_type,
        "entity_id": second.entity_id,
        "details": second.details,
        "severity": second.severity,
        "ip_address": second.ip_address,
        "prev_hash": second.prev_hash,
        "document_hash": second.document_hash,
        "provider_response": second.provider_response,
    }
    payload = json.dumps(data, sort_keys=True, default=str).encode()
    expected = hashlib.sha256(bytes.fromhex(first.hash) + payload).hexdigest()
    assert second.hash == expected
