import importlib
import sys
from pathlib import Path

import pytest


def test_watchlist_load_rejects_non_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DOCREV_WATCHLIST_FILE', str(tmp_path / 'watch.json'))
    (tmp_path / 'watch.json').write_text('{"user": 123}')
    sys.modules.pop('docreview360.watchlist', None)
    with pytest.raises(ValueError):
        importlib.import_module('docreview360.watchlist')
