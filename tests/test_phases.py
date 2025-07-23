from fastapi.testclient import TestClient

from docreview360.api import app


def test_phase_crud() -> None:
    client = TestClient(app)

    resp = client.get("/phases")
    assert resp.status_code == 200
    baseline = set(resp.json())

    resp = client.post("/phases", json={"name": "Draft"})
    assert resp.status_code == 201
    assert "Draft" in resp.json()

    resp = client.delete("/phases/Draft")
    assert resp.status_code == 204

    resp = client.get("/phases")
    phases = set(resp.json())
    assert phases == baseline
