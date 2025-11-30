import importlib
import sys
from pathlib import Path

import pytest


def test_watchlist_load_rejects_non_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(tmp_path / "watch.json"))
    (tmp_path / "watch.json").write_text('{"user": 123}')
    sys.modules.pop("docreview360.watchlist", None)
    with pytest.raises(ValueError):
        importlib.import_module("docreview360.watchlist")


def test_watchlist_load_invalid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(tmp_path / "watch.json"))
    (tmp_path / "watch.json").write_text("{bad json")
    sys.modules.pop("docreview360.watchlist", None)
    with pytest.raises(ValueError):
        importlib.import_module("docreview360.watchlist")


def test_watchlist_load_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREV_WATCHLIST_FILE", str(tmp_path / "watch.json"))
    (tmp_path / "watch.json").write_text('{"u": [1, "2"]}')
    sys.modules.pop("docreview360.watchlist", None)
    wl = importlib.import_module("docreview360.watchlist")
    assert wl.get_watchlist("u") == ["1", "2"]
