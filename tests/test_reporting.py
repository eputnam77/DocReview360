from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth, reporting
from docreview360.api import app


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for a test 'alice' admin user."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass  # user may already exist
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_reporting_endpoints() -> None:
    reporting.reset_metrics_for_testing()
    client = TestClient(app)
    headers = _alice_headers()

    resp = client.post(
        "/projects",
        json={"id": "r1", "name": "Report", "user": "bob", "doc_type": "sample"},
        headers=headers,
    )
    assert resp.status_code == 201

    resp = client.post("/workflows", json={"project": "r1", "phases": ["start", "end"]}, headers=headers)
    assert resp.status_code == 201
    wf_id = resp.json()["id"]

    resp = client.post("/approvals", json={"workflow": wf_id, "reviewer": "alice"}, headers=headers)
    assert resp.status_code == 201

    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "hi", "text/markdown")},
        data={"project": "r1"},
        headers=headers,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    reporting.record_quality_score(doc_id, 0.82, {"version": "q1", "sha256": "stub"})
    reporting.record_compliance_score(doc_id, 0.64, {"version": "c1", "sha256": "stub"})
    reporting.record_routing_snapshot(
        {"<10ms": 1, "10-50ms": 2, "50-100ms": 0, "100ms+": 0},
        {"version": "r1", "sha256": "stub"},
    )

    summary = client.get("/reports/summary", headers=headers).json()
    assert summary["projects"] >= 2
    assert summary["documents"] >= 1
    assert summary["workflows"] >= 1
    assert summary["approvals"] >= 1

    entries = client.get("/reports/dashboard", headers=headers).json()
    entry = next(e for e in entries if e["id"] == "r1")
    assert entry["docs"] == 1
    assert entry["phase"] == "start"
    assert entry["quality_score"] is not None
    assert entry["compliance_score"] is not None
    assert entry["routing_latency"]["<10ms"] == 1
    assert "critic_models" in entry

    widgets = client.get("/dashboard/widgets", headers=headers).json()
    assert "avg_quality_score" in widgets
    assert "routing_latency" in widgets

    assert isinstance(client.get("/reports/throughput", headers=headers).json(), list)
    assert isinstance(client.get("/reports/workload", headers=headers).json(), dict)

    counts = client.get("/dashboard/doc-types", headers=headers).json()
    assert counts["sample"] >= 1

    csv_resp = client.get("/reports/summary.csv", headers=headers)
    header, _values = csv_resp.text.strip().splitlines()
    assert "avg_quality_score" in header
