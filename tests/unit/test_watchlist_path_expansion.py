import importlib
from pathlib import Path

import pytest


def test_watchlist_file_expands_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point HOME to our temp directory so ``~`` resolves inside it
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", "~/custom_watch.json")

    # Import and reload module so it picks up env vars
    import docreview360.watchlist as wl
    wl = importlib.reload(wl)

    expected = tmp_path / "custom_watch.json"
    assert wl.WATCHLIST_FILE == expected

    # Ensure that saving creates the directory and file under the expanded path
    wl._watchlist.clear()
    wl.toggle_watch("user", "proj")
    assert expected.exists()


def test_watchlist_file_expands_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom paths may include environment variables which should be expanded."""

    monkeypatch.setenv("BASE", str(tmp_path))
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", "$BASE/w.json")

    import docreview360.watchlist as wl
    wl = importlib.reload(wl)

    expected = tmp_path / "w.json"
    assert wl.WATCHLIST_FILE == expected
    wl._watchlist.clear()
    wl.toggle_watch("u", "p")
    assert wl.get_watchers("p") == ["u"]
    assert expected.exists()
