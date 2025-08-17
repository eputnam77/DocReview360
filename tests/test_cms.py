"""Tests for CMS persistence helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from docreview360.api import update_document_endpoint
from docreview360.cms import save_to_cms
from docreview360.config import Config
from docreview360.documents import DocumentModel, import_document
from docreview360.sharepoint import SharePointClient


def test_save_to_cms_uploads_via_client() -> None:
    doc = DocumentModel(id="abc", content="hello")
    cfg = Config(database="sqlite", editor="tiptap", cms="sharepoint", auth="oidc")

    uploaded: dict[str, bytes] = {}

    def fake_upload(path: str, data: bytes) -> str:
        uploaded[path] = data
        return "item42"

    client = cast(SharePointClient, SimpleNamespace(upload_file=fake_upload))
    item_id = save_to_cms(doc, config=cfg, client=client)
    assert item_id == "item42"
    assert uploaded == {"abc.md": b"hello"}


@pytest.mark.asyncio
async def test_update_endpoint_calls_save(monkeypatch) -> None:
    doc = import_document("doc.md", b"start")
    cfg = Config(database="sqlite", editor="tiptap", cms="sharepoint", auth="oidc")

    monkeypatch.setattr("docreview360.api.Config.load", lambda path: cfg)

    called: dict[str, DocumentModel] = {}

    def fake_save(document: DocumentModel, *, config: Config) -> str:
        called["doc"] = document
        return "id"

    monkeypatch.setattr("docreview360.api.save_to_cms", fake_save)

    body = DocumentModel(id=doc.id, content="next")
    updated = await update_document_endpoint(doc.id, body)
    assert called["doc"].id == doc.id
    assert updated.content == "next"
