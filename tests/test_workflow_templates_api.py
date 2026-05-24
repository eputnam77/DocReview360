from datetime import timedelta

import pytest
from docreview360 import auth, db_store, rbac, workflows
from docreview360.api import app
from fastapi.testclient import TestClient
from sqlalchemy import text


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _user_headers(username: str) -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(username, "Password!1Secure")
    except Exception:
        pass
    rbac.set_user_roles(username, ["user"])
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _custom_template_payload(name: str) -> dict:
    return {
        "name": name,
        "description": "Custom workflow template",
        "steps": [
            {"role": "Reviewer", "required": True},
            {"role": "Approver", "required": True},
        ],
    }


@pytest.fixture(autouse=True)
def _isolated_state(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    user_db = tmp_path / "users.db"
    roles_db = tmp_path / "roles.db"
    app_db = tmp_path / "docreview360.db"

    monkeypatch.setenv("DOCREVIEW360_USER_DB", str(user_db))
    monkeypatch.setenv("DOCREVIEW360_RBAC_DB", str(roles_db))
    auth.configure_user_repository(user_db)
    rbac.configure_role_repository(roles_db)
    rbac.reset_role_assignments(include_defaults=False)
    db_store.reset_db(f"sqlite:///{app_db}")
    monkeypatch.setattr(workflows, "DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE", True)
    workflows.reset_workflow_templates()
    workflows.workflows.clear()
    yield
    db_store.reset_db(None)
    workflows.reset_workflow_templates()
    workflows.workflows.clear()


def test_workflow_template_crud_and_persistence() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    payload = _custom_template_payload("Custom Flow")
    res = client.post("/workflow-templates", json=payload, headers=hdrs)
    assert res.status_code == 201
    created = res.json()
    assert created["id"] == "Custom Flow"
    assert created["usage"] == 0
    with db_store.get_db().session() as conn:
        row = conn.execute(
            text("SELECT name FROM workflow_template_records WHERE id = :id"),
            {"id": "Custom Flow"},
        ).fetchone()
    assert row is not None and row[0] == "Custom Flow"

    res = client.get("/workflow-templates", headers=hdrs)
    assert res.status_code == 200
    templates = res.json()
    assert any(item["id"] == "Custom Flow" for item in templates)

    updated_payload = _custom_template_payload("Custom Flow v2")
    updated_payload["description"] = "Updated description"
    res = client.put("/workflow-templates/Custom%20Flow", json=updated_payload, headers=hdrs)
    assert res.status_code == 200
    updated = res.json()
    assert updated["id"] == "Custom Flow v2"
    assert updated["description"] == "Updated description"
    with db_store.get_db().session() as conn:
        old_row = conn.execute(
            text("SELECT 1 FROM workflow_template_records WHERE id = :id"),
            {"id": "Custom Flow"},
        ).fetchone()
    assert old_row is None

    workflows.reset_workflow_templates(keep_file=True)
    res = client.get("/workflow-templates/Custom%20Flow%20v2", headers=hdrs)
    assert res.status_code == 200
    persisted = res.json()
    assert persisted["id"] == "Custom Flow v2"

    res = client.delete("/workflow-templates/Custom%20Flow%20v2", headers=hdrs)
    assert res.status_code == 204
    res = client.get("/workflow-templates/Custom%20Flow%20v2", headers=hdrs)
    assert res.status_code == 404
    workflows.reset_workflow_templates(keep_file=True)
    res = client.get("/workflow-templates/Custom%20Flow%20v2", headers=hdrs)
    assert res.status_code == 404


def test_workflow_template_writes_require_admin() -> None:
    client = TestClient(app)
    payload = _custom_template_payload("User Flow")

    res = client.post("/workflow-templates", json=payload, headers=_user_headers("eve"))

    assert res.status_code == 403


def test_custom_template_used_for_project_workflow() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    payload = _custom_template_payload("Project Flow")
    res = client.post("/workflow-templates", json=payload, headers=hdrs)
    assert res.status_code == 201

    proj_res = client.post(
        "/projects",
        json={"name": "Template Project", "phase": "Draft", "workflow": "Project Flow"},
        headers=hdrs,
    )
    assert proj_res.status_code == 201
    project = proj_res.json()
    workflow_id = project["workflow"]
    assert workflow_id

    wf_res = client.get(f"/workflows/{workflow_id}", headers=hdrs)
    assert wf_res.status_code == 200
    wf_data = wf_res.json()
    assert wf_data["template"] == "Project Flow"
    roles = [step["role"] for step in wf_data["approval_steps"]]
    assert roles == ["Reviewer", "Approver"]


def test_document_type_default_workflow_template_must_exist() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    res = client.post(
        "/document-types",
        json={
            "name": "Stale Default Doc",
            "template": "<h1>Stale</h1>",
            "workflow": ["Draft Development"],
            "default_workflow_template_id": "missing-template",
        },
        headers=hdrs,
    )

    assert res.status_code == 400
    assert "Default workflow template not found" in res.json()["message"]


def test_workflow_template_rename_updates_phase_and_document_type_links() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    res = client.post(
        "/workflow-templates",
        json=_custom_template_payload("Linked Flow"),
        headers=hdrs,
    )
    assert res.status_code == 201

    res = client.post(
        "/document-types",
        json={
            "name": "Linked Doc",
            "template": "<h1>Linked</h1>",
            "workflow": ["Draft Development"],
            "default_workflow_template_id": "Linked Flow",
        },
        headers=hdrs,
    )
    assert res.status_code == 201

    res = client.put(
        "/phases/Draft%20Development/workflow-template",
        json={"workflow_template_id": "Linked Flow"},
        headers=hdrs,
    )
    assert res.status_code == 200

    res = client.put(
        "/workflow-templates/Linked%20Flow",
        json=_custom_template_payload("Linked Flow v2"),
        headers=hdrs,
    )
    assert res.status_code == 200
    assert res.json()["id"] == "Linked Flow v2"

    doc_type = client.get("/document-types/Linked%20Doc", headers=hdrs).json()
    assert doc_type["default_workflow_template_id"] == "Linked Flow v2"

    phase_config = client.get("/phases/config", headers=hdrs).json()
    linked_phase = next(item for item in phase_config if item["name"] == "Draft Development")
    assert linked_phase["workflow_template_id"] == "Linked Flow v2"


def test_workflow_template_delete_blocks_active_workflows() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    res = client.post(
        "/workflow-templates",
        json=_custom_template_payload("Active Flow"),
        headers=hdrs,
    )
    assert res.status_code == 201

    project = client.post(
        "/projects",
        json={"name": "Active Flow Project", "phase": "Draft Development", "workflow": "Active Flow"},
        headers=hdrs,
    )
    assert project.status_code == 201

    res = client.delete("/workflow-templates/Active%20Flow", headers=hdrs)

    assert res.status_code == 409
    assert "workflow" in res.json()["message"]


def test_phase_create_rejects_whitespace_duplicate() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    res = client.post("/phases", json={"name": " Human Review "}, headers=hdrs)
    assert res.status_code == 201

    res = client.post("/phases", json={"name": "Human Review"}, headers=hdrs)

    assert res.status_code == 409
