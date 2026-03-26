"""Tests for CMS persistence helpers."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import cast

import pytest
from docreview360 import auth
from docreview360.api.documents_router import (
    CmsExportRequest,
    CmsImportRequest,
    RevisionCreate,
    create_revision_endpoint,
    export_document_to_cms,
    import_document_from_cms,
    update_document_endpoint,
)
from docreview360.cms import fetch_from_cms, save_to_cms
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


def test_save_to_cms_strips_cms_setting(monkeypatch) -> None:
    """Whitespace around the CMS name should not prevent uploads."""
    doc = DocumentModel(id="xyz", content="hi")
    cfg = Config(database="sqlite", editor="tiptap", cms=" sharepoint ", auth="oidc")

    uploaded: dict[str, bytes] = {}

    class Dummy:
        def upload_file(self, path: str, data: bytes) -> str:
            uploaded[path] = data
            return "x1"

    monkeypatch.setattr("docreview360.cms.client_from_env", lambda: Dummy())
    item_id = save_to_cms(doc, config=cfg)
    assert item_id == "x1"
    assert uploaded == {"xyz.md": b"hi"}


@pytest.mark.asyncio
async def test_update_endpoint_calls_save(monkeypatch) -> None:
    doc = import_document("doc.md", b"start")
    # Intentionally include whitespace around the CMS value to ensure the API
    # normalises the configuration before deciding whether to save.
    cfg = Config(database="sqlite", editor="tiptap", cms=" sharepoint ", auth="oidc")

    monkeypatch.setattr(Config, "load", lambda path: cfg)

    called: dict[str, DocumentModel] = {}

    def fake_save(document: DocumentModel, *, config: Config) -> str:
        called["doc"] = document
        return "id"

    monkeypatch.setattr(sys.modules["docreview360.api.documents_router"], "save_to_cms", fake_save)

    body = DocumentModel(id=doc.id, content="next")
    mock_user = auth.User(username="alice", active=True)
    updated = await update_document_endpoint(doc.id, body, current_user=mock_user)
    assert called["doc"].id == doc.id
    assert updated.content == "next"


@pytest.mark.asyncio
async def test_revision_endpoint_calls_save(monkeypatch) -> None:
    doc = import_document("doc.md", b"start")
    cfg = Config(database="sqlite", editor="tiptap", cms=" sharepoint ", auth="oidc")

    monkeypatch.setattr(Config, "load", lambda path: cfg)

    called: dict[str, DocumentModel] = {}

    def fake_save(document: DocumentModel, *, config: Config) -> str:
        called["doc"] = document
        return "id"

    monkeypatch.setattr(sys.modules["docreview360.api.documents_router"], "save_to_cms", fake_save)

    body = RevisionCreate(content="next")
    mock_user = auth.User(username="alice", active=True)
    result = await create_revision_endpoint(doc.id, body, x_user="alice", current_user=mock_user)
    assert result["revisionId"]
    assert called["doc"].id == doc.id


def test_local_cms_saves_and_fetches(monkeypatch, tmp_path) -> None:
    doc = DocumentModel(id="local-doc", content="hello")
    cfg = Config(database="sqlite", editor="tiptap", cms="local", auth="oidc")

    monkeypatch.setattr(
        "docreview360.cms.load_settings",
        lambda: {"cms": {"local": {"bucket": str(tmp_path)}}},
    )
    item_id = save_to_cms(doc, config=cfg)
    assert item_id == "local-doc.md"
    stored = tmp_path / "local-doc.md"
    assert stored.read_text() == "hello"

    payload = fetch_from_cms(item_id, config=cfg)
    assert payload == b"hello"


@pytest.mark.asyncio
async def test_import_and_export_endpoints_with_local_cms(monkeypatch, tmp_path) -> None:
    cfg = Config(database="sqlite", editor="tiptap", cms="local", auth="oidc")
    monkeypatch.setattr(Config, "load", lambda path: cfg)
    monkeypatch.setattr(
        "docreview360.cms.load_settings",
        lambda: {"cms": {"local": {"bucket": str(tmp_path)}}},
    )

    mock_user = auth.User(username="alice", active=True)
    doc = import_document("doc.md", b"seed")
    export_response = await export_document_to_cms(
        doc.id, CmsExportRequest(fmt="markdown"), current_user=mock_user
    )
    assert export_response.item_id == f"{doc.id}.md"

    import_response = await import_document_from_cms(
        CmsImportRequest(item_id=export_response.item_id, filename="imported.md"),
        current_user=mock_user,
    )
    assert import_response.content == "seed"
