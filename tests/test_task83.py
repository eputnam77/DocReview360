from __future__ import annotations

import json
from pathlib import Path

import pytest

from docreview360.metabase import MetabaseClient, load_dashboards


def test_get_chart() -> None:
    client = MetabaseClient()
    assert client.get_chart("42") == {"id": "42", "title": "Chart 42"}


def test_heatmap() -> None:
    client = MetabaseClient()
    data = client.heatmap("p1")
    assert data and len(data) == 3


def test_load_dashboards(tmp_path: Path) -> None:
    path = tmp_path / "dash.json"
    path.write_text(json.dumps({"charts": [{"id": "1", "title": "Foo"}]}))
    data = load_dashboards(path)
    client = MetabaseClient(data)
    assert client.get_chart("1")["title"] == "Foo"


def test_load_dashboards_requires_chart_list(tmp_path: Path) -> None:
    path = tmp_path / "dash.json"
    path.write_text(json.dumps({"charts": "oops"}))
    with pytest.raises(ValueError, match="charts.*list"):
        load_dashboards(path)
