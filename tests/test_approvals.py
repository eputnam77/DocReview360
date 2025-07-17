from fastapi.testclient import TestClient

from docreview360.api import app


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
