import json
from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from docreview360 import watchlist
from docreview360.api import app


def test_watchlist_toggle(tmp_path: Path, monkeypatch: Any) -> None:
    file = tmp_path / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    reload(watchlist)

    assert watchlist.toggle_watch("alice", "p1") == ["p1"]
    assert watchlist.get_watchlist("alice") == ["p1"]
    assert watchlist.toggle_watch("alice", "p1") == []


def test_watchlist_api(tmp_path: Path, monkeypatch: Any) -> None:
    file = tmp_path / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    reload(watchlist)
    client = TestClient(app)
    resp = client.post("/watchlist/p1", json={"user": "bob"})
    assert resp.status_code == 201
    assert resp.json() == ["p1"]
    resp = client.get("/watchlist/bob")
    assert resp.json() == ["p1"]


def test_watchlist_custom_path(tmp_path: Path, monkeypatch: Any) -> None:
    """Writing to a nested custom path creates parent directories."""
    file = tmp_path / "nested" / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    reload(watchlist)
    watchlist.toggle_watch("alice", "p1")
    assert json.loads(file.read_text()) == {"alice": ["p1"]}


def test_get_watchers(tmp_path: Path, monkeypatch: Any) -> None:
    """Retrieve users watching a project."""
    file = tmp_path / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    reload(watchlist)
    watchlist.toggle_watch("alice", "p1")
    watchlist.toggle_watch("bob", "p1")
    assert watchlist.get_watchers("p1") == ["alice", "bob"]


def test_load_existing_and_invalid_json(tmp_path: Path, monkeypatch: Any) -> None:
    """_load handles valid and malformed JSON files."""
    file = tmp_path / "watch.json"
    file.write_text(json.dumps({"alice": ["p1"]}))
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    reload(watchlist)
    assert watchlist.get_watchlist("alice") == ["p1"]
    # now corrupt the file
    file.write_text("{bad json")
    reload(watchlist)
    assert watchlist.get_watchlist("alice") == []


def test_toggle_watch_validation() -> None:
    with pytest.raises(ValueError):
        watchlist.toggle_watch("", "p1")
