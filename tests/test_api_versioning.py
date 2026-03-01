from fastapi.testclient import TestClient

from docreview360.api import app


def test_api_v1_alias_for_ping() -> None:
    client = TestClient(app)

    base = client.get("/ping")
    v1 = client.get("/api/v1/ping")

    assert base.status_code == 200
    assert v1.status_code == 200
    assert v1.json() == base.json()


def test_api_v1_alias_for_health() -> None:
    client = TestClient(app)

    base = client.get("/health")
    v1 = client.get("/api/v1/health")

    assert base.status_code == 200
    assert v1.status_code == 200
    assert v1.json() == base.json()
