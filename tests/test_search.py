from datetime import datetime

from fastapi.testclient import TestClient

from docreview360.api import app


def _doc_ids(resp):
    return {doc["id"] for doc in resp.json()}


def test_search_returns_matching_document() -> None:
    client = TestClient(app)
    content = "This document contains special keywords"
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", content, "text/markdown")},
        data={"project": "p1", "user": "alice", "priority": 1},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get("/search", params={"q": "special"})
    assert resp.status_code == 200
    assert any(d["id"] == doc_id for d in resp.json())

    resp = client.get("/search", params={"q": "special", "project": "p1"})
    assert len(resp.json()) == 1


def test_search_supports_project_name_and_date_filter() -> None:
    client = TestClient(app)

    # Create a project explicitly
    from docreview360 import search as search_module

    search_module.add_project(search_module.ProjectModel(id="p2", name="Very Secret Project"))

    content = "Top content"
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", content, "text/markdown")},
        data={"project": "p2", "user": "bob", "priority": 2},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    from docreview360 import documents as doc_module

    old_date = datetime(2020, 1, 1)
    doc_module.documents[doc_id].date = old_date

    resp = client.get("/search", params={"q": "Secret"})
    assert any(d["id"] == doc_id for d in resp.json())

    resp = client.get(
        "/search",
        params={
            "q": "Secret",
            "after": "2021-01-01T00:00:00",
        },
    )
    assert not any(d["id"] == doc_id for d in resp.json())


def test_search_multiword_user_and_priority_filters() -> None:
    client = TestClient(app)

    resp = client.post(
        "/documents/import",
        files={"file": ("a.md", "Alpha Beta", "text/markdown")},
        data={"project": "p3", "user": "alice", "priority": 2},
    )
    doc_a = resp.json()["id"]

    resp = client.post(
        "/documents/import",
        files={"file": ("b.md", "Alpha Gamma", "text/markdown")},
        data={"project": "p3", "user": "bob", "priority": 1},
    )
    doc_b = resp.json()["id"]

    resp = client.get("/search", params={"q": "Alpha Beta"})
    assert _doc_ids(resp) == {doc_a}

    resp = client.get("/search", params={"q": "Alpha", "user": "bob"})
    assert _doc_ids(resp) == {doc_b}

    resp = client.get("/search", params={"q": "Alpha", "priority": 2})
    assert _doc_ids(resp) == {doc_a}


def test_search_index_updates_after_edit() -> None:
    client = TestClient(app)

    resp = client.post(
        "/documents/import",
        files={"file": ("c.md", "Old text", "text/markdown")},
        data={"project": "p4", "user": "carol", "priority": 1},
    )
    doc_id = resp.json()["id"]

    # Document initially searchable by old content
    resp = client.get("/search", params={"q": "Old"})
    assert _doc_ids(resp) == {doc_id}

    # Update the document
    client.put(
        f"/documents/{doc_id}",
        json={"id": doc_id, "content": "New text", "history": []},
    )

    # Old term should no longer match
    resp = client.get("/search", params={"q": "Old"})
    assert doc_id not in _doc_ids(resp)

    # New term should match
    resp = client.get("/search", params={"q": "New"})
    assert _doc_ids(resp) == {doc_id}
