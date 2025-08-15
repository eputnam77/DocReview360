import asyncio

import pytest

from docreview360.approvals import approvals, create_approval, handle_signature_return, send_for_signature
from docreview360.integrations.signature import documenso
from docreview360.logs import clear_logs, logs


def test_verification_failure_logged_with_ip():
    approvals.clear()
    clear_logs()
    doc = b"hello"
    appr = create_approval("wf1", "alice", "doc1", document=doc, signature_provider="documenso")
    send_for_signature(appr.id, "doc1", "alice")
    documenso.complete_signature(appr.signature_id)

    with pytest.raises(ValueError):
        asyncio.run(handle_signature_return(appr.signature_id, document=doc, client_ip="1.2.3.4"))

    entry = next(e for e in reversed(logs) if e.action == "signature_verification_failed")
    assert entry.actor == "alice"
    assert entry.context.get("ip") == "1.2.3.4"
