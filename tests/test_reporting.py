from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360 import reporting


def test_reporting_endpoints() -> None:
    reporting.reset_metrics_for_testing()
    client = TestClient(app)

    resp = client.post(
        "/projects",
        json={"id": "r1", "name": "Report", "user": "bob", "doc_type": "sample"},
    )
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
    doc_id = resp.json()["id"]

    reporting.record_quality_score(doc_id, 0.82, {"version": "q1", "sha256": "stub"})
    reporting.record_compliance_score(doc_id, 0.64, {"version": "c1", "sha256": "stub"})
    reporting.record_routing_snapshot(
        {"<10ms": 1, "10-50ms": 2, "50-100ms": 0, "100ms+": 0},
        {"version": "r1", "sha256": "stub"},
    )

    summary = client.get("/reports/summary").json()
    assert summary["projects"] >= 2
    assert summary["documents"] >= 1
    assert summary["workflows"] >= 1
    assert summary["approvals"] >= 1

    entries = client.get("/reports/dashboard").json()
    entry = next(e for e in entries if e["id"] == "r1")
    assert entry["docs"] == 1
    assert entry["phase"] == "start"
    assert entry["quality_score"] is not None
    assert entry["compliance_score"] is not None
    assert entry["routing_latency"]["<10ms"] == 1
    assert "critic_models" in entry

    widgets = client.get("/dashboard/widgets").json()
    assert "avg_quality_score" in widgets
    assert "routing_latency" in widgets

    assert isinstance(client.get("/reports/throughput").json(), list)
    assert isinstance(client.get("/reports/workload").json(), dict)

    counts = client.get("/dashboard/doc-types").json()
    assert counts["sample"] >= 1

    csv_resp = client.get("/reports/summary.csv")
    header, _values = csv_resp.text.strip().splitlines()
    assert "avg_quality_score" in header
