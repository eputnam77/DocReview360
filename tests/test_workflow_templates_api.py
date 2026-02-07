from fastapi.testclient import TestClient

from docreview360 import workflows
from docreview360.api import app


def _custom_template_payload(name: str) -> dict:
    return {
        "name": name,
        "description": "Custom workflow template",
        "steps": [
            {"role": "Reviewer", "required": True},
            {"role": "Approver", "required": True},
        ],
    }


def test_workflow_template_crud_and_persistence(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(workflows, "WORKFLOW_TEMPLATES_FILE", tmp_path / "workflow_templates.json")
    workflows.reset_workflow_templates()
    client = TestClient(app)

    payload = _custom_template_payload("Custom Flow")
    res = client.post("/workflow-templates", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["id"] == "Custom Flow"
    assert created["usage"] == 0
    assert (tmp_path / "workflow_templates.json").exists()

    res = client.get("/workflow-templates")
    assert res.status_code == 200
    templates = res.json()
    assert any(item["id"] == "Custom Flow" for item in templates)

    updated_payload = _custom_template_payload("Custom Flow v2")
    updated_payload["description"] = "Updated description"
    res = client.put("/workflow-templates/Custom%20Flow", json=updated_payload)
    assert res.status_code == 200
    updated = res.json()
    assert updated["id"] == "Custom Flow v2"
    assert updated["description"] == "Updated description"

    workflows.reset_workflow_templates(keep_file=True)
    res = client.get("/workflow-templates/Custom%20Flow%20v2")
    assert res.status_code == 200
    persisted = res.json()
    assert persisted["id"] == "Custom Flow v2"

    res = client.delete("/workflow-templates/Custom%20Flow%20v2")
    assert res.status_code == 204
    res = client.get("/workflow-templates/Custom%20Flow%20v2")
    assert res.status_code == 404


def test_custom_template_used_for_project_workflow(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(workflows, "WORKFLOW_TEMPLATES_FILE", tmp_path / "workflow_templates.json")
    workflows.reset_workflow_templates()
    client = TestClient(app)

    payload = _custom_template_payload("Project Flow")
    res = client.post("/workflow-templates", json=payload)
    assert res.status_code == 201

    proj_res = client.post(
        "/projects",
        json={"name": "Template Project", "phase": "Draft", "workflow": "Project Flow"},
    )
    assert proj_res.status_code == 201
    project = proj_res.json()
    workflow_id = project["workflow"]
    assert workflow_id

    wf_res = client.get(f"/workflows/{workflow_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()
    assert wf_data["template"] == "Project Flow"
    roles = [step["role"] for step in wf_data["approval_steps"]]
    assert roles == ["Reviewer", "Approver"]
