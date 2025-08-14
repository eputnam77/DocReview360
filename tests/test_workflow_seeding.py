from fastapi.testclient import TestClient

from docreview360.api import app

client = TestClient(app)


def test_workflows_seeded():
    resp = client.get("/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
