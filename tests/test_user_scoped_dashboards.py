from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth, reporting
from docreview360.api import app
from docreview360.approvals import approvals, create_approval
from docreview360.search import ProjectModel, add_project, projects
from docreview360.workflows import create_workflow, workflows


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}", "X-User": "alice"}


def _bob_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "bob",
            auth.DEMO_USER_DEFAULTS.get("bob", {}).get("password", "bobpassword123"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}", "X-User": "bob"}


def _cleanup() -> None:
    """Clear global state for clean test runs."""
    projects.clear()
    approvals.clear()
    workflows.clear()


def _setup() -> None:
    _cleanup()  # Ensure clean state
    add_project(ProjectModel(id="pA", name="A", user="alice"))
    add_project(ProjectModel(id="pB", name="B", user="bob"))
    wf_a = create_workflow("pA", ["draft"])
    wf_b = create_workflow("pB", ["draft"])
    create_approval(wf_a.id, "alice", "docA")
    create_approval(wf_b.id, "bob", "docB")


def test_dashboard_filtering_by_user() -> None:
    reporting.reset_metrics_for_testing()
    _setup()
    client = TestClient(app)

    alice_hdrs = _alice_headers()
    bob_hdrs = _bob_headers()

    resp = client.get("/reports/dashboard", headers=alice_hdrs)
    assert resp.status_code == 200
    ids = [entry["id"] for entry in resp.json()]
    assert ids == ["pA"]

    resp = client.get("/dashboard/widgets", headers=alice_hdrs)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned"] == 1
    assert data["pending_approvals"] == 1
    assert "avg_quality_score" in data

    resp = client.get("/dashboard/widgets", headers=bob_hdrs)
    assert resp.json()["assigned"] == 1
