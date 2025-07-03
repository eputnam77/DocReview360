from fastapi.testclient import TestClient

from docuflow.api import app


def test_ranked_search_and_export() -> None:
    client = TestClient(app)
    client.post(
        "/documents/import",
        files={"file": ("a.md", "foo bar foo", "text/markdown")},
    )
    client.post(
        "/documents/import",
        files={"file": ("b.md", "bar baz", "text/markdown")},
    )

    resp = client.get("/search/export", params={"q": "foo", "fmt": "json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["score"] > 0

    csv_resp = client.get("/search/export", params={"q": "foo", "fmt": "csv"})
    assert csv_resp.headers["content-type"].startswith("text/csv")
