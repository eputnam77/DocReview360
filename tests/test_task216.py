import json
from importlib import import_module, reload
from pathlib import Path
from typing import Any


def test_task216_toggle(tmp_path: Path, monkeypatch: Any) -> None:
    file = tmp_path / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    watchlist = import_module("docreview360.watchlist")
    reload(watchlist)

    lst1 = watchlist.toggle_watch("alice", "p1")
    assert "p1" in lst1
    assert json.loads(file.read_text())["alice"] == ["p1"]

    reload(watchlist)
    lst2 = watchlist.toggle_watch("alice", "p2")
    assert set(lst2) == {"p1", "p2"}
    reload(watchlist)
    assert "p1" not in watchlist.toggle_watch("alice", "p1")
