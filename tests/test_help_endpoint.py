from docreview360.api import app
from fastapi.testclient import TestClient


def test_help_page() -> None:
    client = TestClient(app)
    resp = client.get("/help")
    assert resp.status_code == 200
    assert "Getting Started" in resp.text
