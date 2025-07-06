import httpx
import pytest

from docuflow.metabase import fetch_card_csv, fetch_dashboards


def test_fetch_dashboards(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        req = httpx.Request("GET", url)
        return httpx.Response(200, json=[{"id": 1, "name": "Main"}], request=req)

    monkeypatch.setattr("httpx.get", fake_get)
    data = fetch_dashboards("http://mb", "tok")
    assert data == [{"id": 1, "name": "Main"}]


def test_fetch_card_csv(monkeypatch):
    def fake_post(url, headers=None, timeout=None):
        req = httpx.Request("POST", url)
        return httpx.Response(200, text="a,b\n1,2", request=req)

    monkeypatch.setattr("httpx.post", fake_post)
    csv = fetch_card_csv("http://mb", 3, "tok")
    assert "1,2" in csv
