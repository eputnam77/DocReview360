from fastapi.testclient import TestClient

from docuflow.api import app


def test_dashboard_updates_after_signature() -> None:
    client = TestClient(app)
    client.post("/projects", json={"id": "d1", "name": "Doc"})
    wf = client.post("/workflows", json={"project": "d1", "phases": ["draft", "signed"]}).json()
    appr = client.post("/approvals", json={"workflow": wf["id"], "reviewer": "bob"}).json()
    doc = client.post(
        "/documents/import",
        files={"file": ("f.txt", b"hi", "text/plain")},
        data={"project": "d1"},
    ).json()
    sig = client.post(
        f"/sign/{doc['id']}",
        data={"user": "alice", "workflow": wf["id"], "approval": appr["id"]},
    ).json()["id"]

    entry = next(e for e in client.get("/reports/dashboard").json() if e["id"] == "d1")
    assert entry["pending_approvals"] == 1

    client.post("/hooks/documenso", json={"id": sig, "status": "signed"})
    entry2 = next(e for e in client.get("/reports/dashboard").json() if e["id"] == "d1")
    assert entry2["pending_approvals"] == 0
