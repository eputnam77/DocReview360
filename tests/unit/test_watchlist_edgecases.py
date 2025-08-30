"""Additional watchlist edge case tests."""

from pathlib import Path

import pytest

import docreview360.watchlist as wl


def test_load_invalid_json_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A corrupted JSON file should not be silently swallowed."""
    bad_file = tmp_path / "watchlist.json"
    bad_file.write_text("{this is: invalid}")
    monkeypatch.setattr(wl, "WATCHLIST_FILE", bad_file)
    with pytest.raises(ValueError):
        wl._load()


def test_load_non_mapping_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Structured JSON that is not an object should be rejected."""
    bad_file = tmp_path / "watchlist.json"
    bad_file.write_text('["a"]')
    monkeypatch.setattr(wl, "WATCHLIST_FILE", bad_file)
    with pytest.raises(ValueError):
        wl._load()


def test_toggle_normalises_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Leading/trailing whitespace should be ignored when toggling watches."""
    file_path = tmp_path / "watchlist.json"
    monkeypatch.setattr(wl, "WATCHLIST_FILE", file_path)
    wl._watchlist.clear()
    wl.toggle_watch(" alice ", " project-1 ")
    assert wl.get_watchlist("alice") == ["project-1"]
    # Toggling again with normalised strings should remove the entry
    wl.toggle_watch("alice", "project-1")
    assert wl.get_watchlist("alice") == []


def test_rejects_blank_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only user or project ids should be rejected."""
    file_path = tmp_path / "watchlist.json"
    monkeypatch.setattr(wl, "WATCHLIST_FILE", file_path)
    wl._watchlist.clear()

    with pytest.raises(ValueError):
        wl.toggle_watch("  ", "proj")
    with pytest.raises(ValueError):
        wl.toggle_watch("alice", "   ")
    with pytest.raises(ValueError):
        wl.get_watchlist(" ")
    with pytest.raises(ValueError):
        wl.get_watchers(" ")
