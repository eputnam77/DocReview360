from datetime import datetime, timedelta, timezone

import pytest
from docreview360.api import app
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
        json={"workflow": wf_id, "reviewer": "alice"},
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
        json={"workflow": wf["id"], "reviewer": "bob", "due_at": due},
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

    appr = create_approval("wf1", "bob")
    appr.state = "approved"
    assert reset_approval(appr.id, True)
    assert appr.state == "pending"

    appr.state = "approved"
    assert not reset_approval(appr.id, False)
    assert appr.state == "approved"


def test_handle_signature_return_hash_validation() -> None:
    """handle_signature_return should validate document hash."""

    from docreview360.approvals import (
        create_approval,
        handle_signature_return,
        send_for_signature,
    )

    doc = b"hello"
    appr = create_approval("wf42", "carol", document=doc)
    send_for_signature(appr.id, "doc42", "carol")
    # Valid document should mark approved
    handle_signature_return(appr.signature_id, document=doc)
    assert appr.state == "approved"

    # Mismatch should raise
    appr2 = create_approval("wf43", "dave", document=b"orig")
    send_for_signature(appr2.id, "doc43", "dave")
    with pytest.raises(ValueError):
        handle_signature_return(appr2.signature_id, document=b"tampered")
