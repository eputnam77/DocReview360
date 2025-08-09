from fastapi.testclient import TestClient

from docreview360.api import app


def test_sign_approval_flow() -> None:
    client = TestClient(app)
    wf = client.post("/workflows", json={"project": "p42", "phases": ["draft", "signed"]}).json()
    appr = client.post("/approvals", json={"workflow": wf["id"], "reviewer": "jane"}).json()

    resp = client.post(f"/approvals/{appr['id']}/sign")
    assert resp.status_code == 200
    sig_id = resp.json()["id"]

    client.post(f"/sign/{sig_id}/complete")

    appr2 = client.get(f"/approvals/{appr['id']}").json()
    assert appr2["state"] == "approved"
    assert appr2["signature"] == sig_id
