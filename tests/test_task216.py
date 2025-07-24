import json
from importlib import reload


def test_task216_toggle(tmp_path, monkeypatch):
    file = tmp_path / "watch.json"
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(file))
    import docreview360.stubs.task216 as t216

    reload(t216)
    lst1 = t216.toggle_watch("alice", "p1")
    assert "p1" in lst1
    assert json.loads(file.read_text())["alice"] == ["p1"]

    reload(t216)
    lst2 = t216.toggle_watch("alice", "p2")
    assert set(lst2) == {"p1", "p2"}
    reload(t216)
    assert "p1" not in t216.toggle_watch("alice", "p1")
