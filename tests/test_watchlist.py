from importlib import reload

from docreview360 import watchlist
from docreview360.api import app
from fastapi.testclient import TestClient


def test_watchlist_toggle(tmp_path, monkeypatch):
    file = tmp_path / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    reload(watchlist)

    assert watchlist.toggle_watch("alice", "p1") == ["p1"]
    assert watchlist.get_watchlist("alice") == ["p1"]
    assert watchlist.toggle_watch("alice", "p1") == []


def test_watchlist_api(tmp_path, monkeypatch):
    file = tmp_path / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    reload(watchlist)
    client = TestClient(app)
    resp = client.post("/watchlist/p1", json={"user": "bob"})
    assert resp.status_code == 201
    assert resp.json() == ["p1"]
    resp = client.get("/watchlist/bob")
    assert resp.json() == ["p1"]
