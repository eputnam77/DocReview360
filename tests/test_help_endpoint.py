from fastapi.testclient import TestClient
from docreview360.api import app


def test_help_page() -> None:
    client = TestClient(app)
    resp = client.get("/help")
    assert resp.status_code == 200
    assert "Getting Started" in resp.text
