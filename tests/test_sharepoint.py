from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import List
from uuid import uuid4

from docreview360.records import sync_to_sharepoint
from docreview360.sharepoint import SharePointClient


class DummyResponse:
    def __init__(self, *, json_data=None, content: bytes = b"") -> None:
        self._json = json_data or {}
        self.content = content

    def raise_for_status(self) -> None:  # pragma: no cover - no http
        return None

    def json(self):  # pragma: no cover - no http
        return self._json


def test_client_upload_builds_correct_request(monkeypatch):
    calls: List[str] = []

    def fake_put(url: str, headers, data: bytes, timeout: float) -> DummyResponse:
        calls.append(url)
        assert headers["Authorization"] == "Bearer token"
        assert data == b"hello"
        assert timeout > 0
        return DummyResponse(json_data={"id": "42"})

    monkeypatch.setattr("docreview360.sharepoint.requests.put", fake_put)

    client = SharePointClient(site_id="s", drive_id="d", token="token")
    item_id = client.upload_file("folder/file.txt", b"hello")
    assert item_id == "42"
    assert calls == [
        "https://graph.microsoft.com/v1.0/sites/s/drives/d/root:/folder/file.txt:/content"
    ]


def test_client_download_and_versions(monkeypatch):
    def fake_get(url: str, headers, timeout: float):
        assert timeout > 0
        if url.endswith("/content"):
            return DummyResponse(content=b"data")
        return DummyResponse(json_data={"value": [{"id": "1"}, {"id": "2"}]})

    monkeypatch.setattr("docreview360.sharepoint.requests.get", fake_get)

    client = SharePointClient(site_id="s", drive_id="d", token="token")
    data = client.download_file("item")
    versions = client.list_versions("item")
    assert data == b"data"
    assert versions == ["1", "2"]


def test_sync_to_sharepoint_uses_client(monkeypatch):
    src = Path(".tmp") / f"sharepoint-sync-{uuid4().hex}" / "archives"
    src.mkdir(parents=True, exist_ok=True)
    (src / "a.txt").write_text("x")

    uploaded: List[str] = []

    def fake_upload(path: str, data: bytes) -> str:
        uploaded.append(path)
        assert data == b"x"
        return "id"

    client = SimpleNamespace(upload_file=fake_upload)
    count = sync_to_sharepoint(src, client=client)
    assert count == 1
    assert uploaded == ["a.txt"]
