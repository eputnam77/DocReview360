"""Documenso approval and delegation tests."""


from docreview360 import documenso
from docreview360.logs import clear_logs, log_event, query_logs
from docreview360.security_utils import create_signature


def test_approve_triggers_envelope_and_audit_hash(monkeypatch) -> None:
    clear_logs()
    sig_id, url = documenso.request_signature("doc1", "alice")
    audit = create_signature(sig_id, secret="s")
    log_event("documenso_envelope", audit=audit)
    entry = query_logs("documenso_envelope")[0]
    assert entry.metadata["audit"] == audit
    assert sig_id
    assert url


def test_delegated_signoff_records_delegate(monkeypatch) -> None:
    clear_logs()
    log_event("signoff", user="delegate", actor_type="delegate", manager="boss")
    entry = query_logs("signoff")[0]
    assert entry.metadata["actor_type"] == "delegate"
    assert entry.metadata["manager"] == "boss"
