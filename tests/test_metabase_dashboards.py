from typing import Any, Dict, Optional

import httpx
import pytest
from docreview360.metabase import fetch_card_csv, fetch_dashboards


def test_fetch_dashboards(monkeypatch: Any) -> None:
    def fake_get(
        url: str, headers: Optional[Dict[str, Any]] = None, timeout: Optional[int] = None
    ) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(200, json=[{"id": 1, "name": "Main"}], request=req)

    monkeypatch.setattr("httpx.get", fake_get)
    data = fetch_dashboards("http://mb", "tok")
    assert data == [{"id": 1, "name": "Main"}]


def test_fetch_card_csv(monkeypatch: Any) -> None:
    def fake_post(
        url: str, headers: Optional[Dict[str, Any]] = None, timeout: Optional[int] = None
    ) -> httpx.Response:
        req = httpx.Request("POST", url)
        return httpx.Response(200, text="a,b\n1,2", request=req)

    monkeypatch.setattr("httpx.post", fake_post)
    csv = fetch_card_csv("http://mb", 3, "tok")
    assert "1,2" in csv


def test_fetch_dashboards_requires_base_url() -> None:
    with pytest.raises(ValueError, match="base_url required"):
        fetch_dashboards("   ", "tok")


def test_fetch_card_csv_requires_positive_id() -> None:
    with pytest.raises(ValueError, match="card_id must be positive"):
        fetch_card_csv("http://mb", 0, "tok")
