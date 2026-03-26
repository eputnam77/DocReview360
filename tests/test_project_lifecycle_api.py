from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360 import search as search_module
from docreview360.api import app
from docreview360.rbac import add_role


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


def test_project_lifecycle_persists_and_deletes() -> None:
    client = TestClient(app)
    headers = _alice_headers()

    project_data = {"id": "proj-1", "name": "Project One", "user": "alice"}
    create_resp = client.post("/projects", json=project_data, headers=headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["id"] == "proj-1"
    assert created["name"] == "Project One"

    list_resp = client.get("/projects", headers=headers)
    assert list_resp.status_code == 200
    project_ids = {item["id"] for item in list_resp.json()["items"]}
    assert "proj-1" in project_ids

    if not auth.USER_REPOSITORY.get_user("alice"):
        auth.USER_REPOSITORY.create_user("alice", "Password!1234", otp_secret="123456")
    rbac.reset_role_assignments(include_defaults=False)
    add_role("alice", "manager")
    token = auth.create_access_token({"sub": "alice"})
    manager_resp = client.get(
        "/dashboard/manager",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert manager_resp.status_code == 200
    manager_projects = {item["id"] for item in manager_resp.json()["projects"]}
    assert "proj-1" in manager_projects

    user_resp = client.get("/dashboard/user", headers=headers)
    assert user_resp.status_code == 200
    user_data = user_resp.json()
    user_projects = {item["id"] for item in (user_data["projects"] if isinstance(user_data, dict) else user_data)}
    assert "proj-1" in user_projects

    update_resp = client.put(
        "/projects/proj-1",
        json={"name": "Project One Updated", "description": "Updated"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Project One Updated"
    assert updated["description"] == "Updated"

    delete_resp = client.delete("/projects/proj-1", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["id"] == "proj-1"

    missing_resp = client.get("/projects/proj-1", headers=headers)
    assert missing_resp.status_code == 404

    list_after = client.get("/projects", headers=headers)
    assert list_after.status_code == 200
    after_ids = {item["id"] for item in list_after.json()["items"]}
    assert "proj-1" not in after_ids

    manager_after = client.get(
        "/dashboard/manager",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert manager_after.status_code == 200
    manager_ids = {item["id"] for item in manager_after.json()["projects"]}
    assert "proj-1" not in manager_ids

    user_after = client.get("/dashboard/user", headers=headers)
    assert user_after.status_code == 200
    user_ids = {item["id"] for item in user_after.json()["projects"]}
    assert "proj-1" not in user_ids

    search_module._reload_state_from_repository()
    assert "proj-1" not in search_module.projects
