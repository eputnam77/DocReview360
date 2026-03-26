from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient


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
    return {"Authorization": f"Bearer {token}"}


def test_phase_crud() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    resp = client.get("/phases")
    assert resp.status_code == 200
    baseline = set(resp.json())

    resp = client.post("/phases", json={"name": "Draft"}, headers=hdrs)
    assert resp.status_code == 201
    assert "Draft" in resp.json()

    resp = client.delete("/phases/Draft", headers=hdrs)
    assert resp.status_code == 204

    resp = client.get("/phases")
    phases = set(resp.json())
    assert phases == baseline


def test_phase_workflow_template_link_config_round_trip() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    template_name = "Phase Link Test Flow"
    create_template = client.post(
      "/workflow-templates",
      json={
          "name": template_name,
          "description": "Phase link test template",
          "steps": [{"role": "Reviewer", "required": True}],
      },
      headers=hdrs,
    )
    assert create_template.status_code in {201, 409}

    create_phase = client.post("/phases", json={"name": "Phase Link Test"}, headers=hdrs)
    assert create_phase.status_code == 201

    try:
      config_resp = client.get("/phases/config")
      assert config_resp.status_code == 200
      config_payload = config_resp.json()
      assert any(item.get("name") == "Phase Link Test" for item in config_payload)

      set_link_resp = client.put(
          "/phases/Phase%20Link%20Test/workflow-template",
          json={"workflow_template_id": template_name},
          headers=hdrs,
      )
      assert set_link_resp.status_code == 200
      assert set_link_resp.json()["workflow_template_id"] == template_name

      config_after_set = client.get("/phases/config")
      assert config_after_set.status_code == 200
      phase_entry = next(
          item for item in config_after_set.json() if item.get("name") == "Phase Link Test"
      )
      assert phase_entry["workflow_template_id"] == template_name

      clear_link_resp = client.put(
          "/phases/Phase%20Link%20Test/workflow-template",
          json={"workflow_template_id": None},
          headers=hdrs,
      )
      assert clear_link_resp.status_code == 200
      assert clear_link_resp.json()["workflow_template_id"] is None
    finally:
      client.delete("/phases/Phase%20Link%20Test", headers=hdrs)
      client.delete(f"/workflow-templates/{template_name.replace(' ', '%20')}", headers=hdrs)
