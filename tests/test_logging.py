from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.logs import clear_logs


def test_logging_records_actions() -> None:
    clear_logs()
    client = TestClient(app)

    # create project logs event
    resp = client.post("/projects", json={"id": "l1", "name": "Log", "user": "alice"})
    assert resp.status_code == 201

    # import document logs event
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
        data={"project": "l1", "user": "alice"},
    )
    assert resp.status_code == 201

    headers = {"X-User": "alice"}
    resp = client.get("/logs", headers=headers)
    events = resp.json()
    actions = {e["action"] for e in events}
    assert "create_project" in actions
    assert "import_document" in actions

    first_id = events[0]["id"]
    resp = client.get("/logs", params={"log_id": first_id}, headers=headers)
    found = resp.json()
    assert len(found) == 1 and found[0]["id"] == first_id

    resp = client.get("/logs", params={"action": "import_document"}, headers=headers)
    filtered = resp.json()
    assert len(filtered) == 1
    assert filtered[0]["details"]["filename"] == "doc.md"

    resp = client.get("/logs", params={"severity": "info", "limit": 1}, headers=headers)
    assert len(resp.json()) == 1
