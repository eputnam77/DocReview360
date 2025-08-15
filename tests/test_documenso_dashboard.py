from fastapi.testclient import TestClient

from docreview360.api import app


def test_dashboard_updates_after_signature() -> None:
    client = TestClient(app)
    client.post("/projects", json={"id": "d1", "name": "Doc"})
    wf = client.post("/workflows", json={"project": "d1", "phases": ["draft", "signed"]}).json()
    doc = client.post(
        "/documents/import",
        files={"file": ("f.txt", b"hi", "text/plain")},
        data={"project": "d1"},
    ).json()
    appr = client.post(
        "/approvals",
        json={"workflow": wf["id"], "reviewer": "bob", "doc_id": doc["id"]},
    ).json()
    sig = client.post(f"/approvals/{appr['id']}/sign").json()["id"]

    entry = next(e for e in client.get("/reports/dashboard").json() if e["id"] == "d1")
    pending = entry["pending_approvals"]
    assert pending >= 1

    client.post(
        "/hooks",
        headers={"X-Provider": "documenso"},
        json={"id": sig, "status": "signed"},
    )
    entry2 = next(e for e in client.get("/reports/dashboard").json() if e["id"] == "d1")
    assert entry2["pending_approvals"] == pending - 1
