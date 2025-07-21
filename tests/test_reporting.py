from fastapi.testclient import TestClient

from docreview360.api import app


def test_reporting_endpoints() -> None:
    client = TestClient(app)

    # create project with workflow and document
    resp = client.post("/projects", json={"id": "r1", "name": "Report", "user": "bob"})
    assert resp.status_code == 201

    resp = client.post("/workflows", json={"project": "r1", "phases": ["start", "end"]})
    assert resp.status_code == 201
    wf_id = resp.json()["id"]

    resp = client.post("/approvals", json={"workflow": wf_id, "reviewer": "alice"})
    assert resp.status_code == 201

    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "hi", "text/markdown")},
        data={"project": "r1"},
    )
    assert resp.status_code == 201

    resp = client.get("/reports/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["projects"] >= 2
    assert summary["documents"] >= 1
    assert summary["workflows"] >= 1
    assert summary["approvals"] >= 1

    resp = client.get("/reports/dashboard")
    assert resp.status_code == 200
    entries = resp.json()
    entry = next(e for e in entries if e["id"] == "r1")
    assert entry["docs"] == 1
    assert entry["phase"] == "start"

    resp = client.get("/reports/throughput")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.get("/reports/workload")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)

    resp = client.get("/dashboard/doc-types")
    assert resp.status_code == 200
