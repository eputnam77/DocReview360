import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from docreview360.api import app
from docreview360.approvals import (
    approvals,
    create_approval,
    handle_signature_return,
    send_for_signature,
)
from docreview360.integrations.signature import documenso
from fastapi.testclient import TestClient


def test_approval_lifecycle() -> None:
    client = TestClient(app)
    # create a workflow first
    wf_resp = client.post(
        "/workflows",
        json={"project": "p1", "phases": ["draft", "review"]},
    )
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    resp = client.post(
        "/approvals",
        json={"workflow": wf_id, "reviewer": "alice", "doc_id": "doc1"},
    )
    assert resp.status_code == 201
    approval = resp.json()
    appr_id = approval["id"]
    assert approval["state"] == "pending"

    resp = client.put(
        f"/approvals/{appr_id}",
        json={"state": "approved", "signature": "signed"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"
    assert resp.json()["signature"] == "signed"

    resp = client.get(f"/approvals/{appr_id}")
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"

    resp = client.get("/approvals", params={"workflow": wf_id})
    assert any(a["id"] == appr_id for a in resp.json())


def test_due_date_updates() -> None:
    client = TestClient(app)
    wf = client.post(
        "/workflows",
        json={"project": "p2", "phases": ["draft"]},
    ).json()
    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = client.post(
        "/approvals",
        json={"workflow": wf["id"], "reviewer": "bob", "due_at": due, "doc_id": "doc2"},
    )
    assert resp.status_code == 201
    appr = resp.json()
    # Normalize both datetime strings to handle different ISO formats
    expected_due = due.replace("+00:00", "Z")
    actual_due = appr["due_at"].replace("+00:00", "Z")
    assert actual_due == expected_due
    new_due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp = client.put(
        f"/approvals/{appr['id']}",
        json={"state": "pending", "due_at": new_due},
    )
    assert resp.status_code == 200
    # Normalize both datetime strings to handle different ISO formats
    expected_new_due = new_due.replace("+00:00", "Z")
    actual_new_due = resp.json()["due_at"].replace("+00:00", "Z")
    assert actual_new_due == expected_new_due


def test_reset_approval() -> None:
    """reset_approval should revert approval state when confirmed."""

    from docreview360.approvals import create_approval, reset_approval

    appr = create_approval("wf1", "bob", "doc-reset")
    appr.state = "approved"
    assert reset_approval(
        appr.id,
        True,
        username="alice",
        password="password",
        otp="123456",
        reason="test",
    )
    assert appr.state == "pending"

    appr.state = "approved"
    assert not reset_approval(
        appr.id,
        False,
        username="alice",
        password="password",
        otp="123456",
        reason="test",
    )
    assert appr.state == "approved"


def test_handle_signature_return_hash_validation() -> None:
    """handle_signature_return should validate document hash."""

    from docreview360.approvals import (
        create_approval,
        handle_signature_return,
        send_for_signature,
    )

    doc = b"hello"
    appr = create_approval("wf42", "carol", "doc42", document=doc, signature_provider="documenso")
    send_for_signature(appr.id, "doc42", "carol")
    documenso.complete_signature(appr.signature_id)
    documenso._sig_certificates[appr.signature_id] = hashlib.sha256(doc).hexdigest()
    # Valid document should mark approved
    asyncio.run(handle_signature_return(appr.signature_id, document=doc))
    assert appr.state == "approved"

    # Mismatch should raise
    appr2 = create_approval(
        "wf43",
        "dave",
        "doc43",
        document=b"orig",
        signature_provider="documenso",
    )
    send_for_signature(appr2.id, "doc43", "dave")
    documenso.complete_signature(appr2.signature_id)
    documenso._sig_certificates[appr2.signature_id] = hashlib.sha256(b"orig").hexdigest()
    with pytest.raises(ValueError):
        asyncio.run(handle_signature_return(appr2.signature_id, document=b"tampered"))


def test_signature_invalidated() -> None:
    """handle_signature_return should reject invalid signatures."""

    from docreview360.approvals import (
        create_approval,
        handle_signature_return,
        send_for_signature,
    )

    doc = b"hello"
    appr = create_approval("wf99", "carol", "doc99", document=doc, signature_provider="documenso")
    send_for_signature(appr.id, "doc99", "carol")
    # mark as completed but without certificate so verification fails
    documenso.complete_signature(appr.signature_id)
    with pytest.raises(ValueError):
        asyncio.run(handle_signature_return(appr.signature_id, document=doc))


def test_send_for_signature_authorization_and_lock() -> None:
    approvals.clear()
    appr = create_approval("wf1", "alice", "doc1")
    with pytest.raises(PermissionError):
        send_for_signature(appr.id, "doc1", "bob")
    appr2 = create_approval("wf1", "alice", "doc2", delegates=["bob"])
    send_for_signature(appr2.id, "doc2", "bob")

    doc = b"hello"
    appr3 = create_approval("wf2", "alice", "doc3", document=doc, signature_provider="documenso")
    send_for_signature(appr3.id, "doc3", "alice")
    documenso.complete_signature(appr3.signature_id)
    documenso._sig_certificates[appr3.signature_id] = hashlib.sha256(doc).hexdigest()
    asyncio.run(handle_signature_return(appr3.signature_id, document=doc))
    with pytest.raises(ValueError):
        send_for_signature(appr3.id, "doc3", "alice")
