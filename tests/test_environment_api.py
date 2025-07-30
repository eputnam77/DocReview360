from docreview360.api import app
from docreview360.environment import add_environment
from fastapi.testclient import TestClient


def test_environment_list_and_switch(tmp_path, monkeypatch):
    path = tmp_path / "env.yaml"
    add_environment("dev", "http://dev", "green", path)
    add_environment("prod", "http://prod", "red", path)
    monkeypatch.setattr("docreview360.environment.ENV_FILE", path)
    client = TestClient(app)

    res = client.get("/environments")
    assert res.status_code == 200
    data = res.json()
    assert "dev" in data["envs"] and "prod" in data["envs"]

    res = client.post("/environments/prod")
    assert res.status_code == 200
    assert res.json()["url"] == "http://prod"
    assert client.get("/environments").json()["current"]["url"] == "http://prod"
