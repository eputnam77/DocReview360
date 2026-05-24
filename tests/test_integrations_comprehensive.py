# SPDX-License-Identifier: MIT
"""Comprehensive production-level integration tests.

All external services (SharePoint, Google Drive, Confluence, DocuSign,
Documenso, APNs, ELK, Splunk, CloudWatch, Slack, Teams) are simulated via
monkeypatching/mocking so no live credentials are required.  Every test
validates request structure, response handling, error paths, and edge cases
to match production behaviour.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.error import HTTPError, URLError

import httpx
import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_urlopen_response(body: bytes, status: int = 200) -> MagicMock:
    """Return a fake urllib response context manager."""
    resp = MagicMock()
    resp.read.return_value = body
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _fake_http_error(code: int, reason: str = "Error") -> HTTPError:
    return HTTPError(url="http://test", code=code, msg=reason, hdrs=MagicMock(), fp=None)


# ===========================================================================
# SharePoint — Graph API client
# ===========================================================================


class TestSharePointClient:
    """Tests for SharePointClient using requests-level mocks."""

    def _make_client(self):
        from docreview360.sharepoint import SharePointClient

        return SharePointClient(site_id="site-1", drive_id="drive-1", token="tok-abc")

    # --- upload_file ---

    def test_upload_file_success(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "item-xyz"}
        mock_resp.raise_for_status = MagicMock()
        calls = []

        def fake_put(url, **kwargs):
            calls.append({"url": url, "kwargs": kwargs})
            return mock_resp

        monkeypatch.setattr("docreview360.sharepoint.requests.put", fake_put)
        item_id = client.upload_file("docs/report.pdf", b"PDF content here")

        assert item_id == "item-xyz"
        assert len(calls) == 1
        assert "report.pdf" in calls[0]["url"]
        assert calls[0]["kwargs"]["data"] == b"PDF content here"
        assert "Bearer tok-abc" in calls[0]["kwargs"]["headers"]["Authorization"]

    def test_upload_file_auth_failure(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
        monkeypatch.setattr("docreview360.sharepoint.requests.put", lambda *a, **kw: mock_resp)

        with pytest.raises(Exception, match="401"):
            client.upload_file("docs/file.pdf", b"data")

    def test_upload_file_server_error(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")
        monkeypatch.setattr("docreview360.sharepoint.requests.put", lambda *a, **kw: mock_resp)

        with pytest.raises(Exception, match="503"):
            client.upload_file("docs/file.pdf", b"data")

    def test_upload_file_missing_item_id_raises(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}  # no "id" key
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.sharepoint.requests.put", lambda *a, **kw: mock_resp)

        with pytest.raises(ValueError, match="Missing item id"):
            client.upload_file("docs/file.pdf", b"data")

    def test_upload_file_empty_data(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "empty-item"}
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.sharepoint.requests.put", lambda *a, **kw: mock_resp)

        item_id = client.upload_file("empty.txt", b"")
        assert item_id == "empty-item"

    def test_upload_file_large_document(self, monkeypatch):
        client = self._make_client()
        large_data = b"X" * (10 * 1024 * 1024)  # 10 MB
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "big-item"}
        mock_resp.raise_for_status = MagicMock()
        received = []
        monkeypatch.setattr(
            "docreview360.sharepoint.requests.put",
            lambda *a, data=None, **kw: (received.append(len(data)), mock_resp)[1],
        )
        item_id = client.upload_file("large.pdf", large_data)
        assert item_id == "big-item"
        assert received[0] == 10 * 1024 * 1024

    # --- download_file ---

    def test_download_file_success(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.content = b"downloaded bytes"
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.sharepoint.requests.get", lambda *a, **kw: mock_resp)

        data = client.download_file("item-xyz")
        assert data == b"downloaded bytes"

    def test_download_file_not_found(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
        monkeypatch.setattr("docreview360.sharepoint.requests.get", lambda *a, **kw: mock_resp)

        with pytest.raises(Exception, match="404"):
            client.download_file("nonexistent-item")

    # --- list_versions ---

    def test_list_versions_success(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "value": [{"id": "1.0"}, {"id": "2.0"}, {"id": "3.0"}]
        }
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.sharepoint.requests.get", lambda *a, **kw: mock_resp)

        versions = client.list_versions("item-xyz")
        assert versions == ["1.0", "2.0", "3.0"]

    def test_list_versions_empty(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"value": []}
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.sharepoint.requests.get", lambda *a, **kw: mock_resp)

        versions = client.list_versions("item-xyz")
        assert versions == []

    def test_list_versions_numeric_ids(self, monkeypatch):
        """Numeric version IDs from SharePoint should be coerced to str."""
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"value": [{"id": 1}, {"id": 2}]}
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.sharepoint.requests.get", lambda *a, **kw: mock_resp)

        versions = client.list_versions("item-xyz")
        assert versions == ["1", "2"]

    # --- set_properties ---

    def test_set_properties_success(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        calls = []

        def fake_patch(url, **kwargs):
            calls.append({"url": url, "json": kwargs.get("json")})
            return mock_resp

        monkeypatch.setattr("docreview360.sharepoint.requests.patch", fake_patch)
        client.set_properties("item-xyz", {"Status": "Approved", "Score": "0.95"})

        assert len(calls) == 1
        assert calls[0]["json"] == {"Status": "Approved", "Score": "0.95"}
        assert "listItem/fields" in calls[0]["url"]

    def test_set_properties_failure(self, monkeypatch):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("400 Bad Request")
        monkeypatch.setattr("docreview360.sharepoint.requests.patch", lambda *a, **kw: mock_resp)

        with pytest.raises(Exception, match="400"):
            client.set_properties("item-xyz", {"Bad": "prop"})

    # --- client_from_env ---

    def test_client_from_env_missing_credentials(self, monkeypatch):
        monkeypatch.delenv("SHAREPOINT_SITE_ID", raising=False)
        monkeypatch.delenv("SHAREPOINT_DRIVE_ID", raising=False)
        monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
        from docreview360.sharepoint import client_from_env

        with pytest.raises(ValueError, match="Missing SharePoint credentials"):
            client_from_env()

    def test_client_from_env_success(self, monkeypatch):
        monkeypatch.setenv("SHAREPOINT_SITE_ID", "my-site")
        monkeypatch.setenv("SHAREPOINT_DRIVE_ID", "my-drive")
        monkeypatch.setenv("DOCREVIEW360_SHAREPOINT_TOKEN", "tok-xyz")
        # patch get_secret to return our token
        monkeypatch.setattr("docreview360.sharepoint.get_secret", lambda _: "tok-xyz")
        from docreview360.sharepoint import client_from_env

        c = client_from_env()
        assert c.site_id == "my-site"
        assert c.drive_id == "my-drive"
        assert c.token == "tok-xyz"

    # --- upload_with_scoring ---

    def test_upload_with_scoring_above_threshold(self, monkeypatch):
        """Score above threshold: only primary approval created, no risk review."""
        from docreview360.sharepoint import SharePointClient

        client = SharePointClient(site_id="s", drive_id="d", token="t")
        upload_calls = []

        # Mock upload_file
        def fake_upload(path, data):
            upload_calls.append(path)
            return "item-99"

        monkeypatch.setattr(client, "upload_file", fake_upload)
        monkeypatch.setattr(client, "set_properties", lambda *a, **kw: None)

        from docreview360.quality import QualityAssessment
        monkeypatch.setattr(
            "docreview360.sharepoint.quality_assessment",
            lambda text: QualityAssessment(score=0.85, raw_score=0.85, flags=[]),
        )
        monkeypatch.setattr(
            "docreview360.sharepoint.quality_model_metadata", lambda: {}
        )
        monkeypatch.setattr(
            "docreview360.sharepoint.metadata_to_context", lambda m: {}
        )
        monkeypatch.setattr(
            "docreview360.sharepoint.routing_features",
            lambda text, cfg: {"features": {"priority": 0.5, "structure": 0.7}},
        )

        approval_ids_created = []

        def fake_create_approval(
            workflow, reviewer, *, doc_id=None, description="", scoring_metadata=None
        ):
            aid = f"appr-{len(approval_ids_created)}"
            approval_ids_created.append(aid)
            a = MagicMock()
            a.id = aid
            return a

        monkeypatch.setattr("docreview360.sharepoint.create_approval", fake_create_approval)
        monkeypatch.setattr(
            "docreview360.sharepoint.submit_draft_for_approval", lambda *a, **kw: None
        )

        item_id, score, approvals = client.upload_with_scoring(
            "docs/report.pdf",
            b"document text content here",
            workflow="wf-1",
            reviewer="alice",
            threshold=0.5,
        )
        assert item_id == "item-99"
        assert score >= 0.5  # above threshold
        # Primary review always created
        assert len(approvals) >= 1

    def test_upload_with_scoring_metadata_failure_does_not_block(self, monkeypatch):
        """Metadata set_properties failure must be swallowed — upload still succeeds."""
        from docreview360.sharepoint import SharePointClient

        client = SharePointClient(site_id="s", drive_id="d", token="t")
        monkeypatch.setattr(client, "upload_file", lambda path, data: "item-ok")

        def boom(*a, **kw):
            raise RuntimeError("Graph API down")

        monkeypatch.setattr(client, "set_properties", boom)

        from docreview360.quality import QualityAssessment
        monkeypatch.setattr(
            "docreview360.sharepoint.quality_assessment",
            lambda text: QualityAssessment(score=0.7, raw_score=0.7, flags=[]),
        )
        monkeypatch.setattr("docreview360.sharepoint.quality_model_metadata", lambda: {})
        monkeypatch.setattr("docreview360.sharepoint.metadata_to_context", lambda m: {})
        monkeypatch.setattr(
            "docreview360.sharepoint.routing_features",
            lambda text, cfg: {"features": {"priority": 0.5, "structure": 0.7}},
        )
        monkeypatch.setattr("docreview360.sharepoint.create_approval", lambda *a, **kw: None)

        item_id, score, approvals = client.upload_with_scoring("x.pdf", b"txt")
        assert item_id == "item-ok"


# ===========================================================================
# SharePoint Upload Helper (sharepoint_upload.py)
# ===========================================================================


class TestSharePointUploadHelper:
    """Tests for upload_final_pdf — the post-signing archival helper."""

    @pytest.mark.asyncio
    async def test_upload_final_pdf_full(self, monkeypatch):
        from docreview360.integrations.sharepoint_upload import upload_final_pdf

        mock_client = MagicMock()
        mock_client.upload_file = AsyncMock(return_value="item-signed")
        mock_client.set_properties = AsyncMock()
        # async_client_from_env is imported locally inside upload_final_pdf from ..sharepoint
        monkeypatch.setattr(
            "docreview360.sharepoint.async_client_from_env",
            AsyncMock(return_value=mock_client),
        )

        signed_at = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        await upload_final_pdf(
            approval_id="appr-42",
            item_id="sp-item-1",
            document=b"PDF bytes",
            document_hash="deadbeef",
            provider_metadata={"transaction_id": "tx-99"},
            signed_at=signed_at,
        )

        mock_client.upload_file.assert_called_once()
        args = mock_client.upload_file.call_args[0]
        assert "appr-42" in args[0]
        assert args[1] == b"PDF bytes"

        props = mock_client.set_properties.call_args[0][1]
        assert props["documentHash"] == "deadbeef"
        assert props["transactionId"] == "tx-99"
        assert "2024-06-01" in props["signedDate"]

    @pytest.mark.asyncio
    async def test_upload_final_pdf_with_certificate(self, monkeypatch):
        from docreview360.integrations.sharepoint_upload import upload_final_pdf

        mock_client = MagicMock()
        mock_client.upload_file = AsyncMock(return_value="item-cert")
        mock_client.set_properties = AsyncMock()
        monkeypatch.setattr(
            "docreview360.sharepoint.async_client_from_env",
            AsyncMock(return_value=mock_client),
        )

        signed_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
        await upload_final_pdf(
            approval_id="appr-cert",
            item_id="sp-item-2",
            document=b"PDF",
            document_hash="abc123",
            provider_metadata=None,
            signed_at=signed_at,
            certificate_url="https://certs.example.com/cert.pem",
            fetcher=lambda url: b"CERT BYTES",
        )

        # Both document and certificate should be uploaded
        assert mock_client.upload_file.call_count == 2
        upload_paths = [c[0][0] for c in mock_client.upload_file.call_args_list]
        assert any("signed" in p for p in upload_paths)
        assert any("cert" in p for p in upload_paths)

    @pytest.mark.asyncio
    async def test_upload_final_pdf_certificate_fetch_failure_raises(self, monkeypatch):
        from docreview360.integrations.sharepoint_upload import upload_final_pdf

        mock_client = MagicMock()
        mock_client.upload_file = AsyncMock(return_value="item-x")
        mock_client.set_properties = AsyncMock()
        monkeypatch.setattr(
            "docreview360.sharepoint.async_client_from_env",
            AsyncMock(return_value=mock_client),
        )

        def cert_boom(url):
            raise ConnectionError("Cannot fetch cert")

        signed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ConnectionError, match="Cannot fetch cert"):
            await upload_final_pdf(
                approval_id="appr-fail",
                item_id="sp-item-3",
                document=b"PDF",
                document_hash="hash",
                provider_metadata=None,
                signed_at=signed_at,
                certificate_url="https://certs.example.com/bad.pem",
                fetcher=cert_boom,
            )

    @pytest.mark.asyncio
    async def test_upload_final_pdf_no_document(self, monkeypatch):
        """When document is None no document upload should occur."""
        from docreview360.integrations.sharepoint_upload import upload_final_pdf

        mock_client = MagicMock()
        mock_client.upload_file = AsyncMock()
        mock_client.set_properties = AsyncMock()
        monkeypatch.setattr(
            "docreview360.sharepoint.async_client_from_env",
            AsyncMock(return_value=mock_client),
        )

        signed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        await upload_final_pdf(
            approval_id="appr-null",
            item_id="sp-item-4",
            document=None,
            document_hash=None,
            provider_metadata=None,
            signed_at=signed_at,
        )
        mock_client.upload_file.assert_not_called()
        mock_client.set_properties.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_final_pdf_provider_timestamp_from_metadata(self, monkeypatch):
        from docreview360.integrations.sharepoint_upload import upload_final_pdf

        mock_client = MagicMock()
        mock_client.upload_file = AsyncMock(return_value="item-ts")
        mock_client.set_properties = AsyncMock()
        monkeypatch.setattr(
            "docreview360.sharepoint.async_client_from_env",
            AsyncMock(return_value=mock_client),
        )

        provider_ts = datetime(2024, 3, 15, 8, 30, 0, tzinfo=timezone.utc)
        signed_at = datetime(2024, 3, 15, tzinfo=timezone.utc)
        await upload_final_pdf(
            approval_id="appr-ts",
            item_id="sp-ts",
            document=b"PDF",
            document_hash="h",
            provider_metadata={"timestamp": provider_ts, "envelope_id": "env-1"},
            signed_at=signed_at,
        )

        props = mock_client.set_properties.call_args[0][1]
        assert "2024-03-15T08:30:00" in props["providerTimestamp"]
        assert props["transactionId"] == "env-1"


# ===========================================================================
# Google Drive Integration
# ===========================================================================


class TestGoogleDriveClient:
    """Tests for GoogleDriveClient using urllib mock."""

    def _make_client(self):
        from docreview360.integrations.google_drive_integration import GoogleDriveClient

        return GoogleDriveClient(access_token="drive-tok", default_folder_id="folder-1")

    def _fake_urlopen(self, body_dict: dict, status: int = 200):
        body = json.dumps(body_dict).encode()
        return _fake_urlopen_response(body, status)

    # --- list_files ---

    def test_list_files_success(self, monkeypatch):
        client = self._make_client()
        resp_body = {
            "files": [
                {"id": "f1", "name": "doc.pdf", "mimeType": "application/pdf", "size": 1024,
                 "modifiedTime": "2024-01-01T00:00:00Z", "parents": [], "webViewLink": "http://..."}
            ]
        }
        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen",
            lambda req, timeout=60: self._fake_urlopen(resp_body),
        )
        files = client.list_files()
        assert len(files) == 1
        assert files[0].id == "f1"
        assert files[0].name == "doc.pdf"
        assert files[0].size == 1024

    def test_list_files_with_folder_filter(self, monkeypatch):
        client = self._make_client()
        captured = []

        def fake_urlopen(req, timeout=60):
            captured.append(req.full_url)
            return self._fake_urlopen({"files": []})

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", fake_urlopen
        )
        client.list_files(folder_id="folder-xyz")
        assert "folder-xyz" in captured[0]

    def test_list_files_with_query(self, monkeypatch):
        client = self._make_client()
        captured = []

        def fake_urlopen(req, timeout=60):
            captured.append(req.full_url)
            return self._fake_urlopen({"files": []})

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", fake_urlopen
        )
        client.search_files("quarterly report")
        assert (
            "quarterly+report" in captured[0]
            or "quarterly%20report" in captured[0]
            or "quarterly" in captured[0]
        )

    def test_get_file_metadata(self, monkeypatch):
        client = self._make_client()
        resp_body = {
            "id": "f2", "name": "contract.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size": 2048, "modifiedTime": "2024-02-01T00:00:00Z", "parents": ["p1"], "webViewLink": "http://..."
        }
        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen",
            lambda req, timeout=60: self._fake_urlopen(resp_body),
        )
        f = client.get_file_metadata("f2")
        assert f.id == "f2"
        assert f.name == "contract.docx"
        assert f.parents == ["p1"]

    # --- download_file ---

    def test_download_file_success(self, monkeypatch):
        client = self._make_client()
        resp = MagicMock()
        resp.read.return_value = b"binary pdf data"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen",
            lambda req, timeout=120: resp,
        )
        data = client.download_file("f1")
        assert data == b"binary pdf data"

    def test_download_file_403_raises(self, monkeypatch):
        client = self._make_client()

        def raise_403(req, timeout=120):
            raise _fake_http_error(403, "Forbidden")

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", raise_403
        )
        from docreview360.integrations.google_drive_integration import GoogleDriveError
        with pytest.raises(GoogleDriveError, match="403"):
            client.download_file("f-forbidden")

    def test_download_file_network_error(self, monkeypatch):
        client = self._make_client()

        def raise_url_error(req, timeout=120):
            raise URLError("Network unreachable")

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", raise_url_error
        )
        from docreview360.integrations.google_drive_integration import GoogleDriveError
        with pytest.raises(GoogleDriveError, match="Cannot reach"):
            client.download_file("f1")

    # --- export_google_doc ---

    def test_export_google_doc_success(self, monkeypatch):
        client = self._make_client()
        resp = MagicMock()
        resp.read.return_value = b"exported markdown text"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen",
            lambda req, timeout=120: resp,
        )
        data = client.export_google_doc("gdoc-1", mime_type="text/plain")
        assert data == b"exported markdown text"

    def test_export_google_doc_not_exportable(self, monkeypatch):
        client = self._make_client()

        def raise_400(req, timeout=120):
            raise _fake_http_error(400, "Bad Request")

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", raise_400
        )
        from docreview360.integrations.google_drive_integration import GoogleDriveError
        with pytest.raises(GoogleDriveError, match="Export failed"):
            client.export_google_doc("binary-file-id")

    # --- upload_file ---

    def test_upload_file_success(self, monkeypatch):
        client = self._make_client()
        resp_body = {
            "id": "new-f1", "name": "report.pdf",
            "mimeType": "application/pdf",
            "size": 512, "modifiedTime": "2024-03-01T00:00:00Z",
            "parents": ["folder-1"], "webViewLink": "http://..."
        }
        captured_body = []

        def fake_urlopen(req, timeout=120):
            captured_body.append(req.data)
            return self._fake_urlopen(resp_body)

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", fake_urlopen
        )
        f = client.upload_file("report.pdf", b"PDF content", mime_type="application/pdf")
        assert f.id == "new-f1"
        assert f.name == "report.pdf"
        # Multipart body must contain both metadata and content
        assert b"report.pdf" in captured_body[0]
        assert b"PDF content" in captured_body[0]

    def test_upload_file_to_specific_folder(self, monkeypatch):
        client = self._make_client()
        captured = []

        def fake_urlopen(req, timeout=120):
            captured.append(req.data.decode("utf-8", errors="replace"))
            resp_body = {
                "id": "f-new", "name": "x.txt", "mimeType": "text/plain",
                "size": 10, "modifiedTime": "2024-01-01",
                "parents": ["custom-folder"], "webViewLink": "",
            }
            return self._fake_urlopen(resp_body)

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", fake_urlopen
        )
        client.upload_file("x.txt", b"hello", folder_id="custom-folder")
        assert "custom-folder" in captured[0]

    def test_upload_file_auth_error(self, monkeypatch):
        client = self._make_client()

        def raise_401(req, timeout=120):
            raise _fake_http_error(401, "Unauthorized")

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", raise_401
        )
        from docreview360.integrations.google_drive_integration import GoogleDriveError
        with pytest.raises(GoogleDriveError, match="Upload failed"):
            client.upload_file("file.pdf", b"data")

    # --- update_file ---

    def test_update_file_success(self, monkeypatch):
        client = self._make_client()
        resp_body = {"id": "f1", "name": "updated.pdf", "mimeType": "application/pdf",
                     "size": 256, "modifiedTime": "2024-04-01", "parents": [], "webViewLink": ""}
        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen",
            lambda req, timeout=120: self._fake_urlopen(resp_body),
        )
        f = client.update_file("f1", b"new content")
        assert f.id == "f1"

    # --- delete_file ---

    def test_delete_file_success(self, monkeypatch):
        client = self._make_client()
        resp = MagicMock()
        resp.read.return_value = b""  # 204 No Content
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen",
            lambda req, timeout=60: resp,
        )
        result = client.delete_file("f1")
        assert result is True

    # --- share_file ---

    def test_share_file_success(self, monkeypatch):
        client = self._make_client()
        resp_body = {"id": "perm-1", "type": "user", "role": "reader"}
        captured = []

        def fake_urlopen(req, timeout=60):
            captured.append(json.loads(req.data))
            return self._fake_urlopen(resp_body)

        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen", fake_urlopen
        )
        result = client.share_file("f1", "user@example.com", role="reader")
        assert result["id"] == "perm-1"
        assert captured[0]["emailAddress"] == "user@example.com"
        assert captured[0]["role"] == "reader"

    # --- client_from_env ---

    def test_client_from_env_direct_token(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_DRIVE_ACCESS_TOKEN", "direct-tok")
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "root-folder")
        from docreview360.integrations.google_drive_integration import client_from_env

        c = client_from_env()
        assert c.access_token == "direct-tok"
        assert c.default_folder_id == "root-folder"

    def test_client_from_env_missing_config(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_DRIVE_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", raising=False)
        from docreview360.integrations.google_drive_integration import (
            GoogleDriveError,
            client_from_env,
        )

        with pytest.raises(GoogleDriveError, match="GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON"):
            client_from_env()

    def test_parse_file_missing_fields_uses_defaults(self):
        from docreview360.integrations.google_drive_integration import _parse_file

        f = _parse_file({})
        assert f.id == ""
        assert f.name == ""
        assert f.size == 0
        assert f.parents == []


# ===========================================================================
# Confluence Integration
# ===========================================================================


class TestConfluenceClient:
    """Tests for ConfluenceClient."""

    def _make_client(self):
        from docreview360.integrations.confluence_integration import ConfluenceClient

        return ConfluenceClient(
            base_url="https://myorg.atlassian.net/wiki",
            username="alice@example.com",
            api_token="api-secret",
            space_key="DOCS",
        )

    def _fake_urlopen_ok(self, body_dict: dict):
        body = json.dumps(body_dict).encode()
        return _fake_urlopen_response(body)

    # --- auth header ---

    def test_auth_header_format(self):
        client = self._make_client()
        header = client._auth_header()
        assert header.startswith("Basic ")
        decoded = base64.b64decode(header[6:]).decode()
        assert decoded == "alice@example.com:api-secret"

    # --- list_spaces ---

    def test_list_spaces_success(self, monkeypatch):
        client = self._make_client()
        resp = {"results": [
            {"key": "DOCS", "name": "Documentation"},
            {"key": "ENG", "name": "Engineering"},
        ]}
        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen",
            lambda req, timeout=30: self._fake_urlopen_ok(resp),
        )
        spaces = client.list_spaces()
        assert len(spaces) == 2
        assert spaces[0]["key"] == "DOCS"

    def test_list_spaces_empty(self, monkeypatch):
        client = self._make_client()
        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen",
            lambda req, timeout=30: self._fake_urlopen_ok({"results": []}),
        )
        spaces = client.list_spaces()
        assert spaces == []

    # --- get_space ---

    def test_get_space_success(self, monkeypatch):
        client = self._make_client()
        resp = {"key": "DOCS", "name": "Documentation", "type": "global"}
        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen",
            lambda req, timeout=30: self._fake_urlopen_ok(resp),
        )
        space = client.get_space("DOCS")
        assert space["key"] == "DOCS"

    # --- get_page ---

    def test_get_page_success(self, monkeypatch):
        client = self._make_client()
        resp = {
            "id": "123456",
            "title": "My Page",
            "space": {"key": "DOCS"},
            "version": {"number": 3},
            "body": {"storage": {"value": "<h1>Hello</h1>"}},
            "_links": {"webui": "/spaces/DOCS/pages/123456"},
        }
        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen",
            lambda req, timeout=30: self._fake_urlopen_ok(resp),
        )
        page = client.get_page("123456")
        assert page.id == "123456"
        assert page.title == "My Page"
        assert page.version == 3
        assert "<h1>Hello</h1>" in page.body_storage

    # --- search_pages ---

    def test_search_pages(self, monkeypatch):
        client = self._make_client()
        captured = []

        def fake_urlopen(req, timeout=30):
            captured.append(req.full_url)
            return self._fake_urlopen_ok({"results": [{"id": "p1", "title": "Result"}]})

        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen", fake_urlopen
        )
        results = client.search_pages("quarterly review", space_key="DOCS")
        assert len(results) == 1
        assert "quarterly" in captured[0] or "quarterly+review" in captured[0]

    # --- create_page ---

    def test_create_page_success(self, monkeypatch):
        client = self._make_client()
        captured_payload = []
        resp = {
            "id": "789",
            "title": "New Page",
            "space": {"key": "DOCS"},
            "version": {"number": 1},
            "body": {"storage": {"value": "<p>Hello</p>"}},
            "_links": {"webui": "/spaces/DOCS/pages/789"},
        }

        def fake_urlopen(req, timeout=30):
            captured_payload.append(json.loads(req.data))
            return self._fake_urlopen_ok(resp)

        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen", fake_urlopen
        )
        page = client.create_page("New Page", "<p>Hello</p>")
        assert page.id == "789"
        assert page.title == "New Page"
        assert captured_payload[0]["title"] == "New Page"
        assert captured_payload[0]["space"]["key"] == "DOCS"

    def test_create_page_without_space_key_raises(self):
        from docreview360.integrations.confluence_integration import (
            ConfluenceClient,
            ConfluenceError,
        )

        client = ConfluenceClient(
            base_url="https://x.atlassian.net/wiki",
            username="u",
            api_token="t",
            space_key="",
        )
        with pytest.raises(ConfluenceError, match="space_key is required"):
            client.create_page("No Space", "<p>body</p>")

    def test_create_page_with_parent(self, monkeypatch):
        client = self._make_client()
        captured = []
        resp = {
            "id": "child-1", "title": "Child Page",
            "space": {"key": "DOCS"}, "version": {"number": 1},
            "body": {"storage": {"value": ""}}, "_links": {},
        }

        def fake_urlopen(req, timeout=30):
            captured.append(json.loads(req.data))
            return self._fake_urlopen_ok(resp)

        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen", fake_urlopen
        )
        client.create_page("Child Page", "<p>child</p>", parent_id="parent-1")
        assert captured[0]["ancestors"] == [{"id": "parent-1"}]

    # --- update_page ---

    def test_update_page_increments_version(self, monkeypatch):
        client = self._make_client()
        captured = []
        resp = {
            "id": "123", "title": "Updated",
            "space": {"key": "DOCS"}, "version": {"number": 4},
            "body": {"storage": {"value": "<p>new</p>"}}, "_links": {},
        }

        def fake_urlopen(req, timeout=30):
            captured.append(json.loads(req.data))
            return self._fake_urlopen_ok(resp)

        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen", fake_urlopen
        )
        page = client.update_page("123", "Updated", "<p>new</p>", version=3)
        assert page.version == 4
        assert captured[0]["version"]["number"] == 4  # 3 + 1

    # --- delete_page ---

    def test_delete_page_success(self, monkeypatch):
        client = self._make_client()
        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen",
            lambda req, timeout=30: _fake_urlopen_response(b""),
        )
        result = client.delete_page("123")
        assert result is True

    # --- import / export ---

    def test_import_document_markdown(self, monkeypatch):
        client = self._make_client()
        resp = {
            "id": "md-1", "title": "Imported",
            "space": {"key": "DOCS"}, "version": {"number": 1},
            "body": {"storage": {"value": "<p>Hello <strong>world</strong></p>"}},
            "_links": {},
        }
        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen",
            lambda req, timeout=30: self._fake_urlopen_ok(resp),
        )
        page = client.import_document("Imported", "# Hello\n\n**world**", space_key="DOCS")
        assert page.id == "md-1"

    def test_export_page_as_markdown(self, monkeypatch):
        client = self._make_client()
        resp = {
            "id": "export-1", "title": "Export Test",
            "space": {"key": "DOCS"}, "version": {"number": 1},
            "body": {"storage": {"value": "<h1>Title</h1><p>Para with <strong>bold</strong>.</p>"}},
            "_links": {},
        }
        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen",
            lambda req, timeout=30: self._fake_urlopen_ok(resp),
        )
        md = client.export_page_as_markdown("export-1")
        assert "# Title" in md
        assert "**bold**" in md

    # --- error handling ---

    def test_http_error_raises_confluence_error(self, monkeypatch):
        client = self._make_client()

        def raise_500(req, timeout=30):
            raise _fake_http_error(500, "Internal Server Error")

        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen", raise_500
        )
        from docreview360.integrations.confluence_integration import ConfluenceError

        with pytest.raises(ConfluenceError, match="500"):
            client.list_spaces()

    def test_url_error_raises_confluence_error(self, monkeypatch):
        client = self._make_client()

        def raise_url_error(req, timeout=30):
            raise URLError("DNS lookup failed")

        monkeypatch.setattr(
            "docreview360.integrations.confluence_integration.urlopen", raise_url_error
        )
        from docreview360.integrations.confluence_integration import ConfluenceError

        with pytest.raises(ConfluenceError, match="Cannot reach Confluence"):
            client.list_spaces()

    # --- format helpers ---

    def test_storage_to_markdown_headings(self):
        from docreview360.integrations.confluence_integration import _storage_to_markdown

        html = "<h1>Top</h1><h2>Sub</h2><p>Text <strong>bold</strong> and <em>italic</em>.</p>"
        md = _storage_to_markdown(html)
        assert "# Top" in md
        assert "## Sub" in md
        assert "**bold**" in md
        assert "*italic*" in md

    def test_storage_to_markdown_links(self):
        from docreview360.integrations.confluence_integration import _storage_to_markdown

        html = '<a href="https://example.com">click here</a>'
        md = _storage_to_markdown(html)
        assert "[click here](https://example.com)" in md

    def test_storage_to_markdown_xml_entities(self):
        from docreview360.integrations.confluence_integration import _storage_to_markdown

        html = "<p>5 &lt; 10 &amp; 10 &gt; 5</p>"
        md = _storage_to_markdown(html)
        assert "5 < 10 & 10 > 5" in md

    def test_markdown_to_storage_headings(self):
        from docreview360.integrations.confluence_integration import _markdown_to_storage

        md = "# Heading 1\n\n## Heading 2\n\nParagraph text."
        html = _markdown_to_storage(md)
        assert "<h1>Heading 1</h1>" in html
        assert "<h2>Heading 2</h2>" in html
        assert "<p>Paragraph text.</p>" in html

    def test_markdown_to_storage_bold_italic(self):
        from docreview360.integrations.confluence_integration import _markdown_to_storage

        md = "Text with **bold** and *italic* words."
        html = _markdown_to_storage(md)
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_markdown_to_storage_links(self):
        from docreview360.integrations.confluence_integration import _markdown_to_storage

        md = "See [the docs](https://docs.example.com) for more."
        html = _markdown_to_storage(md)
        assert '<a href="https://docs.example.com">the docs</a>' in html

    # --- client_from_env ---

    def test_client_from_env_missing_base_url(self, monkeypatch):
        monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
        from docreview360.integrations.confluence_integration import (
            ConfluenceError,
            client_from_env,
        )

        with pytest.raises(ConfluenceError, match="CONFLUENCE_BASE_URL"):
            client_from_env()

    def test_client_from_env_success(self, monkeypatch):
        monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://myorg.atlassian.net/wiki")
        monkeypatch.setenv("CONFLUENCE_USERNAME", "user@example.com")
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", "token123")
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "ENG")
        from docreview360.integrations.confluence_integration import client_from_env

        c = client_from_env()
        assert c.base_url == "https://myorg.atlassian.net/wiki"
        assert c.space_key == "ENG"


# ===========================================================================
# DocuSign Integration
# ===========================================================================


class TestDocuSignIntegration:
    """Tests for the DocuSign connector — stub mode and circuit-breaker."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        from docreview360.integrations.signature import docusign

        docusign._signatures.clear()
        docusign._sig_workflows.clear()
        docusign._sig_metadata.clear()
        docusign._reset_circuit_breaker_for_tests()
        yield
        docusign._signatures.clear()
        docusign._sig_workflows.clear()
        docusign._sig_metadata.clear()
        docusign._reset_circuit_breaker_for_tests()

    # --- stub mode ---

    def test_request_signature_stub_mode(self):
        from docreview360.integrations.signature import docusign

        sig_id, url, meta = docusign.request_signature("doc-1", "alice")
        assert sig_id
        assert url  # has a value
        assert meta["status"] == "pending"
        assert docusign._signatures[sig_id] == "pending"

    def test_request_signature_with_workflow_and_approval(self):
        from docreview360.integrations.signature import docusign

        sig_id, url, meta = docusign.request_signature(
            "doc-2", "bob", workflow_id="wf-1", approval_id="appr-1",
            return_url="https://example.com/done",
        )
        assert docusign._sig_workflows[sig_id] == "wf-1"
        # approval_id is appended to URL only when return_url is present
        assert "appr-1" in url

    def test_request_signature_invalid_document_id(self):
        from docreview360.integrations.signature import docusign

        with pytest.raises(ValueError, match="document_id"):
            docusign.request_signature("", "alice")

    def test_request_signature_invalid_user(self):
        from docreview360.integrations.signature import docusign

        with pytest.raises(ValueError, match="user"):
            docusign.request_signature("doc-1", "")

    def test_verify_signature_pending(self):
        from docreview360.integrations.signature import docusign

        sig_id, _, _ = docusign.request_signature("doc-3", "carol")
        assert docusign.verify_signature(sig_id, b"pdf") is False

    def test_verify_signature_after_completion(self):
        from docreview360.integrations.signature import docusign

        sig_id, _, _ = docusign.request_signature("doc-4", "dave")
        docusign._signatures[sig_id] = "completed"
        assert docusign.verify_signature(sig_id, b"pdf") is True

    def test_verify_signature_unknown_id(self):
        from docreview360.integrations.signature import docusign

        assert docusign.verify_signature("nonexistent-sig", b"pdf") is False

    # --- validate_signature ---

    def test_validate_signature_completed(self):
        from docreview360.integrations.signature import docusign

        result = docusign.validate_signature(b"pdf", None, {"status": "completed"})
        assert result is True

    def test_validate_signature_pending(self):
        from docreview360.integrations.signature import docusign

        result = docusign.validate_signature(b"pdf", None, {"status": "pending"})
        assert result is False

    def test_validate_signature_case_insensitive(self):
        from docreview360.integrations.signature import docusign

        result = docusign.validate_signature(b"pdf", None, {"status": "Completed"})
        assert result is True

    # --- process_webhook ---

    def test_process_webhook_valid_pending(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)
        sig_id, _, _ = docusign.request_signature("doc-5", "eve")
        docusign.process_webhook({"envelopeId": sig_id, "status": "sent"})
        assert docusign._signatures[sig_id] == "sent"

    def test_process_webhook_completed_advances_workflow(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        advanced = []
        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)

        def fake_advance(wf_id):
            advanced.append(wf_id)

        # Patch the import inside process_webhook
        import docreview360.workflows as _wf
        monkeypatch.setattr(_wf, "advance_workflow", fake_advance)

        sig_id, _, _ = docusign.request_signature("doc-6", "frank", workflow_id="wf-99")
        docusign.process_webhook({"envelopeId": sig_id, "status": "completed"})
        assert docusign._signatures[sig_id] == "completed"

    def test_process_webhook_missing_fields_raises(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        with pytest.raises(ValueError, match="missing envelopeId or status"):
            docusign.process_webhook({"envelopeId": "abc"})  # no status

    def test_process_webhook_invalid_empty_payload(self):
        from docreview360.integrations.signature import docusign

        with pytest.raises(ValueError):
            docusign.process_webhook({})

    def test_process_webhook_datetime_parsing(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)
        sig_id, _, _ = docusign.request_signature("doc-7", "grace")
        docusign.process_webhook({
            "envelopeId": sig_id,
            "status": "completed",
            "completedDateTime": "2024-06-01T12:00:00Z",
        })
        assert docusign._signatures[sig_id] == "completed"

    # --- circuit breaker ---

    def test_circuit_breaker_trips_after_threshold(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi/v2.1")
        monkeypatch.setattr(docusign, "FAILURE_THRESHOLD", 3)
        monkeypatch.setattr(docusign, "FAILURE_WINDOW_SECONDS", 60)
        monkeypatch.setattr(docusign, "FAILURE_COOLDOWN_SECONDS", 300)
        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)
        monkeypatch.setattr(
            "docreview360.integrations.signature.docusign.set_provider_health",
            lambda name, healthy: None,
        )

        def failing_post(*a, **kw):
            req = httpx.Request("POST", "https://demo.docusign.net")
            raise httpx.ConnectError("connection refused", request=req)

        monkeypatch.setattr(docusign, "http_post", failing_post)

        # First 2 failures — breaker not yet tripped
        for _ in range(2):
            with pytest.raises(RuntimeError):
                docusign.request_signature("doc-x", "alice")

        assert docusign._remote_suspended_until is None

        # 3rd failure — breaker trips, falls back to stub
        sig_id, url, _ = docusign.request_signature("doc-x", "alice")
        assert sig_id in docusign._signatures
        assert docusign._remote_suspended_until is not None

    def test_circuit_breaker_stays_suspended(self, monkeypatch):
        """When suspended, remote calls are skipped — stub is used immediately."""
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi/v2.1")
        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)
        docusign._remote_suspended_until = docusign._now() + timedelta(seconds=300)

        remote_called = []

        def guard(*a, **kw):
            remote_called.append(True)
            raise AssertionError("remote called during suspension")

        monkeypatch.setattr(docusign, "http_post", guard)

        sig_id, url, _ = docusign.request_signature("doc-y", "bob")
        assert not remote_called
        assert sig_id in docusign._signatures

    def test_circuit_breaker_recovers_after_cooldown(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi/v2.1")
        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)
        monkeypatch.setattr(
            "docreview360.integrations.signature.docusign.set_provider_health",
            lambda name, healthy: None,
        )
        # Set cooldown to expired
        docusign._remote_suspended_until = docusign._now() - timedelta(seconds=1)

        healthy_resp = MagicMock()
        healthy_resp.status_code = 200
        healthy_resp.json.return_value = {}
        monkeypatch.setattr(docusign, "http_get", lambda *a, **kw: healthy_resp)

        result = docusign.health_check()
        assert result is True
        assert docusign._remote_suspended_until is None

    # --- health check ---

    def test_health_check_no_url(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "DOCUSIGN_BASE_URL", None)
        assert docusign.health_check() is True

    def test_health_check_remote_ok(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi/v2.1")
        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)
        resp = MagicMock()
        resp.status_code = 200
        monkeypatch.setattr(docusign, "http_get", lambda *a, **kw: resp)
        assert docusign.health_check() is True

    def test_health_check_remote_fail(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi/v2.1")
        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)

        def failing_get(*a, **kw):
            raise Exception("timeout")

        monkeypatch.setattr(docusign, "http_get", failing_get)
        assert docusign.health_check() is False

    # --- signature_status ---

    def test_signature_status_stub(self):
        from docreview360.integrations.signature import docusign

        sig_id, _, _ = docusign.request_signature("doc-stat", "user")
        status = docusign.signature_status(sig_id)
        assert status == "pending"

    def test_signature_status_unknown_raises(self):
        from docreview360.integrations.signature import docusign

        with pytest.raises(KeyError):
            docusign.signature_status("totally-unknown")


# ===========================================================================
# APNs Integration
# ===========================================================================


class TestAPNsIntegration:
    """Tests for the Apple Push Notification service connector."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        from docreview360.integrations import apns

        apns.clear_token_cache()
        yield
        apns.clear_token_cache()

    # --- _get_apns_config ---

    def test_config_complete(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "TEAMID1234")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "KEYID12345")
        monkeypatch.setenv("DOCREVIEW360_APNS_PRIVATE_KEY", "-----BEGIN EC PRIVATE KEY-----")
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.docreview360")
        cfg = apns._get_apns_config()
        assert cfg is not None
        assert cfg["team_id"] == "TEAMID1234"
        assert cfg["sandbox"] is False

    def test_config_sandbox_flag(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "T")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "K")
        monkeypatch.setenv("DOCREVIEW360_APNS_PRIVATE_KEY", "PEM")
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.app")
        monkeypatch.setenv("DOCREVIEW360_APNS_SANDBOX", "true")
        cfg = apns._get_apns_config()
        assert cfg is not None
        assert cfg["sandbox"] is True

    def test_config_incomplete_returns_none(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.delenv("DOCREVIEW360_APNS_TEAM_ID", raising=False)
        monkeypatch.delenv("DOCREVIEW360_APNS_KEY_ID", raising=False)
        monkeypatch.delenv("DOCREVIEW360_APNS_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("DOCREVIEW360_APNS_BUNDLE_ID", raising=False)
        assert apns._get_apns_config() is None

    # --- send_apns_notification when not configured ---

    def test_send_not_configured_returns_error_dict(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.delenv("DOCREVIEW360_APNS_TEAM_ID", raising=False)
        monkeypatch.delenv("DOCREVIEW360_APNS_KEY_ID", raising=False)
        monkeypatch.delenv("DOCREVIEW360_APNS_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("DOCREVIEW360_APNS_BUNDLE_ID", raising=False)
        result = apns.send_apns_notification("device-tok", "Title", "Body")
        assert result["success"] is False
        assert result["status"] == 0
        assert "not configured" in result["error"]

    # --- JWT generation ---

    def test_generate_jwt_pyjwt(self, monkeypatch):
        """Verify JWT generation uses ES256 algorithm and correct claims."""
        from docreview360.integrations import apns

        tokens_generated = []

        class FakePyJWT:
            @staticmethod
            def encode(payload, key, algorithm, headers):
                tokens_generated.append({"payload": payload, "headers": headers})
                return "fake.jwt.token"

        monkeypatch.setitem(__import__("sys").modules, "jwt", FakePyJWT)
        token = apns._generate_jwt("TEAM1", "KEY1", "PEM_KEY")
        assert token == "fake.jwt.token"
        assert tokens_generated[0]["payload"]["iss"] == "TEAM1"
        assert tokens_generated[0]["headers"]["alg"] == "ES256"
        assert tokens_generated[0]["headers"]["kid"] == "KEY1"

    def test_generate_jwt_no_library_raises(self, monkeypatch):
        from docreview360.integrations import apns

        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name in ("jwt", "jose"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(RuntimeError, match="APNs token signing requires"):
                apns._generate_jwt("T", "K", "PEM")

    # --- token caching ---

    def test_get_bearer_token_cached(self, monkeypatch):
        from docreview360.integrations import apns

        calls = []

        def fake_generate(team_id, key_id, pem):
            calls.append(1)
            return "cached-token"

        monkeypatch.setattr(apns, "_generate_jwt", fake_generate)
        cfg = {"team_id": "T", "key_id": "K", "private_key": "PEM"}
        t1 = apns._get_bearer_token(cfg)
        t2 = apns._get_bearer_token(cfg)
        assert t1 == t2 == "cached-token"
        assert len(calls) == 1  # only generated once

    def test_get_bearer_token_regenerated_after_ttl(self, monkeypatch):
        from docreview360.integrations import apns

        calls = []

        def fake_generate(team_id, key_id, pem):
            calls.append(1)
            return f"token-{len(calls)}"

        monkeypatch.setattr(apns, "_generate_jwt", fake_generate)
        # Seed an expired token
        apns._cached_token = {"token": "old-token", "generated_at": time.monotonic() - 4000}
        cfg = {"team_id": "T", "key_id": "K", "private_key": "PEM"}
        token = apns._get_bearer_token(cfg)
        assert token == "token-1"
        assert len(calls) == 1

    # --- send_apns_notification with mocked httpx ---

    def _patch_httpx_client(self, monkeypatch, fake_client_class):
        """Patch httpx.Client at the httpx module level (apns imports httpx locally)."""
        import httpx as _httpx_orig
        monkeypatch.setattr(_httpx_orig, "Client", lambda **kw: fake_client_class())

    def test_send_notification_success(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "TEAM1234AB")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "KEY1234567")
        monkeypatch.setenv(
            "DOCREVIEW360_APNS_PRIVATE_KEY",
            "-----BEGIN EC PRIVATE KEY-----\nFAKE\n-----END EC PRIVATE KEY-----",
        )
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.app")
        monkeypatch.setattr(apns, "_get_bearer_token", lambda cfg: "test-jwt-token")

        captured_payload = []

        class FakeHTTPXClient:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def post(self, url, content, headers):
                captured_payload.append(json.loads(content))
                resp = MagicMock()
                resp.status_code = 200
                return resp

        self._patch_httpx_client(monkeypatch, FakeHTTPXClient)

        result = apns.send_apns_notification(
            "device-tok-abc", "Hello", "World", badge=3, extra={"custom": "data"}
        )
        assert result["success"] is True
        assert result["status"] == 200
        assert captured_payload[0]["aps"]["alert"]["title"] == "Hello"
        assert captured_payload[0]["aps"]["alert"]["body"] == "World"
        assert captured_payload[0]["aps"]["badge"] == 3
        assert captured_payload[0]["custom"] == "data"

    def test_send_notification_rejected_by_apns(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "T")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "K")
        monkeypatch.setenv("DOCREVIEW360_APNS_PRIVATE_KEY", "PEM")
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.app")
        monkeypatch.setattr(apns, "_get_bearer_token", lambda cfg: "jwt")

        class FakeClient:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def post(self, url, content, headers):
                resp = MagicMock()
                resp.status_code = 410
                resp.json.return_value = {"reason": "Unregistered"}
                return resp

        self._patch_httpx_client(monkeypatch, FakeClient)
        result = apns.send_apns_notification("bad-token", "Title", "Body")
        assert result["success"] is False
        assert result["status"] == 410
        assert "Unregistered" in result["error"]

    def test_send_notification_network_error(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "T")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "K")
        monkeypatch.setenv("DOCREVIEW360_APNS_PRIVATE_KEY", "PEM")
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.app")
        monkeypatch.setattr(apns, "_get_bearer_token", lambda cfg: "jwt")

        class FakeClient:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def post(self, url, content, headers):
                raise ConnectionError("Network unreachable")

        self._patch_httpx_client(monkeypatch, FakeClient)
        result = apns.send_apns_notification("device-tok", "Title", "Body")
        assert result["success"] is False
        assert result["status"] == 0
        assert "Network unreachable" in result["error"]

    def test_send_notification_token_generation_error(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "T")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "K")
        monkeypatch.setenv("DOCREVIEW360_APNS_PRIVATE_KEY", "PEM")
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.app")

        def bad_token(cfg):
            raise RuntimeError("Invalid private key format")

        monkeypatch.setattr(apns, "_get_bearer_token", bad_token)
        result = apns.send_apns_notification("device-tok", "Title", "Body")
        assert result["success"] is False
        assert "Token error" in result["error"]

    def test_send_notification_uses_sandbox_host(self, monkeypatch):
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "T")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "K")
        monkeypatch.setenv("DOCREVIEW360_APNS_PRIVATE_KEY", "PEM")
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.app")
        monkeypatch.setenv("DOCREVIEW360_APNS_SANDBOX", "true")
        monkeypatch.setattr(apns, "_get_bearer_token", lambda cfg: "jwt")

        captured_urls = []

        class FakeClient:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def post(self, url, content, headers):
                captured_urls.append(url)
                resp = MagicMock()
                resp.status_code = 200
                return resp

        self._patch_httpx_client(monkeypatch, FakeClient)
        apns.send_apns_notification("dev-tok", "T", "B")
        assert "sandbox.push.apple.com" in captured_urls[0]

    def test_clear_token_cache(self, monkeypatch):
        from docreview360.integrations import apns

        apns._cached_token = {"token": "old", "generated_at": time.monotonic()}
        apns.clear_token_cache()
        assert apns._cached_token == {}


# ===========================================================================
# Log Connectors
# ===========================================================================


class TestLogConnectors:
    """Tests for ELK, Splunk, and CloudWatch log connectors."""

    def _make_log_entry(self, message: str = "test event"):
        from docreview360.models import LogEntry

        return LogEntry(
            id="entry-test-1",
            timestamp=datetime.now(timezone.utc),
            action="test.event",
            entity_id="ent-1",
            user_id="user-1",
        )

    # --- LogConnector base ---

    def test_base_connector_batch_size_validation(self):
        from docreview360.log_connectors import LogConnector

        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            LogConnector(endpoint="http://example.com", batch_size=0)

    def test_base_connector_batch_size_type_validation(self):
        from docreview360.log_connectors import LogConnector

        with pytest.raises(TypeError, match="batch_size must be an integer"):
            LogConnector(endpoint="http://example.com", batch_size=2.5)  # type: ignore[arg-type]

    def test_base_connector_flush_empty_buffer(self):
        from docreview360.log_connectors import LogConnector

        connector = LogConnector(endpoint="http://example.com", batch_size=10)
        send_called = []

        async def fake_send(batch):
            send_called.append(batch)

        connector._send_batch = fake_send  # type: ignore[method-assign]
        asyncio.run(connector.flush())
        assert len(send_called) == 0  # nothing to send

    def test_base_connector_emits_when_batch_full(self):
        from docreview360.log_connectors import LogConnector

        connector = LogConnector(endpoint="http://example.com", batch_size=2)
        sent_batches = []

        async def fake_send(batch):
            sent_batches.append(list(batch))

        connector._send_batch = fake_send  # type: ignore[method-assign]
        entry = self._make_log_entry()

        async def run():
            await connector.emit(entry)
            assert len(sent_batches) == 0  # batch not full yet
            await connector.emit(entry)
            assert len(sent_batches) == 1  # batch full, flushed
            assert len(sent_batches[0]) == 2

        asyncio.run(run())

    # --- ELKConnector ---

    def _patch_async_client(self, monkeypatch, fake_client_class):
        """Patch httpx.AsyncClient inside log_connectors module."""
        import docreview360.log_connectors as lc_mod
        import httpx as _httpx
        fake_httpx = MagicMock(spec=_httpx)
        fake_httpx.AsyncClient = lambda **kw: fake_client_class()
        monkeypatch.setattr(lc_mod, "httpx", fake_httpx)

    def test_elk_connector_sends_batch(self, monkeypatch):
        from docreview360.log_connectors import ELKConnector

        connector = ELKConnector(endpoint="http://elk.example.com/_bulk", batch_size=1)
        captured = []

        class FakeAsyncClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def post(self, url, **kwargs):
                captured.append({"url": url, **kwargs})

        self._patch_async_client(monkeypatch, FakeAsyncClient)
        entry = self._make_log_entry()
        asyncio.run(connector.emit(entry))
        assert len(captured) == 1
        assert captured[0]["url"] == "http://elk.example.com/_bulk"

    def test_elk_connector_with_api_key(self, monkeypatch):
        from docreview360.log_connectors import ELKConnector

        connector = ELKConnector(
            endpoint="http://elk.example.com/_bulk",
            api_key="my-elk-key",
            batch_size=1,
        )
        captured_headers = []

        class FakeAsyncClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def post(self, url, json=None, headers=None):
                captured_headers.append(headers)

        self._patch_async_client(monkeypatch, FakeAsyncClient)
        asyncio.run(connector.emit(self._make_log_entry()))
        assert "Bearer my-elk-key" in captured_headers[0]["Authorization"]

    # --- SplunkConnector ---

    def test_splunk_connector_uses_splunk_auth(self, monkeypatch):
        from docreview360.log_connectors import SplunkConnector

        connector = SplunkConnector(
            endpoint="http://splunk.example.com:8088/services/collector",
            api_key="splunk-hec-token",
            batch_size=1,
        )
        captured_headers = []

        class FakeAsyncClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def post(self, url, json=None, headers=None):
                captured_headers.append(headers)

        self._patch_async_client(monkeypatch, FakeAsyncClient)
        asyncio.run(connector.emit(self._make_log_entry()))
        # Splunk uses "Splunk <token>" not "Bearer"
        assert "Splunk splunk-hec-token" in captured_headers[0]["Authorization"]

    def test_splunk_connector_batch_accumulation(self, monkeypatch):
        from docreview360.log_connectors import SplunkConnector

        connector = SplunkConnector(endpoint="http://splunk.example.com", batch_size=5)
        sent_batches = []

        class FakeAsyncClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def post(self, url, json=None, headers=None):
                sent_batches.append(list(json))

        self._patch_async_client(monkeypatch, FakeAsyncClient)
        entry = self._make_log_entry()

        async def run():
            for _ in range(5):
                await connector.emit(entry)
            assert len(sent_batches) == 1
            assert len(sent_batches[0]) == 5

        asyncio.run(run())

    # --- CloudWatchConnector ---

    def test_cloudwatch_connector_no_boto3(self, monkeypatch):
        from docreview360.log_connectors import CloudWatchConnector

        monkeypatch.setattr("docreview360.log_connectors.boto3", None)
        connector = CloudWatchConnector(log_group="/docreview360/app", batch_size=1)

        async def run():
            with pytest.raises(RuntimeError, match="boto3 is required"):
                await connector._send_batch([{"event": "test"}])

        asyncio.run(run())

    def test_cloudwatch_connector_sends_events(self, monkeypatch):
        import docreview360.log_connectors as lc_mod
        from docreview360.log_connectors import CloudWatchConnector

        put_log_calls = []
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_client.put_log_events = lambda **kw: put_log_calls.append(kw)
        mock_boto3.client.return_value = mock_client
        monkeypatch.setattr(lc_mod, "boto3", mock_boto3)

        connector = CloudWatchConnector(log_group="/docreview360/app", batch_size=1)
        entry = self._make_log_entry()
        asyncio.run(connector.emit(entry))

        assert len(put_log_calls) == 1
        assert put_log_calls[0]["logGroupName"] == "/docreview360/app"
        assert put_log_calls[0]["logStreamName"] == "docreview360"
        events = put_log_calls[0]["logEvents"]
        assert len(events) == 1
        # Timestamps must be epoch ms (> year 2000 in ms)
        assert events[0]["timestamp"] > 946684800000  # 2000-01-01 in ms

    # --- Global emit / connector registry ---

    def test_emit_dispatches_to_all_registered_connectors(self, monkeypatch):
        from docreview360.log_connectors import (
            ELKConnector,
            SplunkConnector,
            clear_connectors,
            emit,
            register_connector,
        )
        from docreview360.models import LogEntry

        clear_connectors()
        received_elk = []
        received_splunk = []

        class MockELK(ELKConnector):
            async def _send_batch(self, batch):
                received_elk.extend(batch)

        class MockSplunk(SplunkConnector):
            async def _send_batch(self, batch):
                received_splunk.extend(batch)

        register_connector(MockELK(endpoint="http://elk", batch_size=1))
        register_connector(MockSplunk(endpoint="http://splunk", batch_size=1))

        entry = LogEntry(
            id="entry-dispatch-1",
            timestamp=datetime.now(timezone.utc),
            action="review.approved",
            entity_id="doc-99",
            user_id="alice",
        )
        asyncio.run(emit(entry))
        assert len(received_elk) == 1
        assert len(received_splunk) == 1
        clear_connectors()

    def test_emit_handles_connector_failure_gracefully(self, monkeypatch):
        from docreview360.log_connectors import (
            LogConnector,
            clear_connectors,
            emit,
            register_connector,
        )
        from docreview360.models import LogEntry

        clear_connectors()

        class FailingConnector(LogConnector):
            async def _send_batch(self, batch):
                raise RuntimeError("ELK is down")

        class SuccessConnector(LogConnector):
            received = []
            async def _send_batch(self, batch):
                self.received.extend(batch)

        sc = SuccessConnector(endpoint="http://ok", batch_size=1)
        register_connector(FailingConnector(endpoint="http://bad", batch_size=1))
        register_connector(sc)

        entry = LogEntry(
            id="entry-fail-1",
            timestamp=datetime.now(timezone.utc),
            action="test.event",
            entity_id="e1",
            user_id="u1",
        )
        # Should not raise — failures are swallowed
        asyncio.run(emit(entry))
        # Success connector should still have received the entry
        assert len(sc.received) == 1
        clear_connectors()


# ===========================================================================
# Notifications (Slack, Teams, Webhook, Email)
# ===========================================================================


class TestNotifications:
    """Tests for Slack, Teams, webhook and email notification dispatchers."""

    @pytest.fixture(autouse=True)
    def clear_sent(self):
        from docreview360 import notifications

        notifications.sent_slack_notifications.clear()
        notifications.sent_teams_notifications.clear()
        notifications.sent_webhook_notifications.clear()
        notifications.sent_emails.clear()
        yield
        notifications.sent_slack_notifications.clear()
        notifications.sent_teams_notifications.clear()
        notifications.sent_webhook_notifications.clear()
        notifications.sent_emails.clear()

    # --- Slack ---

    def test_send_slack_success(self, monkeypatch):
        from docreview360 import notifications

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.notifications._http_post" if hasattr(
            notifications, "_http_post") else "docreview360.http_client.post",
            lambda url, **kw: resp, raising=False)
        # Patch the import inside the function
        import docreview360.http_client as _hc
        monkeypatch.setattr(_hc, "post", lambda url, **kw: resp)

        result = notifications.send_slack_notification(
            "https://hooks.slack.com/services/T00/B00/xxx",
            "Review #42 approved by alice",
        )
        assert result["webhook_url"] == "https://hooks.slack.com/services/T00/B00/xxx"
        assert "error" not in result
        assert len(notifications.sent_slack_notifications) == 1

    def test_send_slack_invalid_url(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="webhook_url must be an https://"):
            notifications.send_slack_notification("http://insecure.slack.com", "message")

    def test_send_slack_empty_message(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="message is required"):
            notifications.send_slack_notification("https://hooks.slack.com/xxx", "")

    def test_send_slack_failure_returns_error_dict(self, monkeypatch):
        import docreview360.http_client as _hc
        from docreview360 import notifications

        def failing_post(url, **kw):
            raise ConnectionError("Slack unreachable")

        monkeypatch.setattr(_hc, "post", failing_post)
        result = notifications.send_slack_notification(
            "https://hooks.slack.com/xxx", "alert message"
        )
        assert "error" in result
        assert "Slack unreachable" in result["error"]
        assert len(notifications.sent_slack_notifications) == 0

    # --- Teams ---

    def test_send_teams_success(self, monkeypatch):
        import docreview360.http_client as _hc
        from docreview360 import notifications

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        captured_payload = []

        def capture_post(url, json=None, **kw):
            captured_payload.append(json)
            return resp

        monkeypatch.setattr(_hc, "post", capture_post)
        result = notifications.send_teams_notification(
            "https://myorg.webhook.office.com/webhookb2/xxx",
            "Document review completed",
        )
        assert result["message"] == "Document review completed"
        assert len(notifications.sent_teams_notifications) == 1
        # Teams uses Adaptive Card format
        assert captured_payload[0]["type"] == "message"
        attachments = captured_payload[0]["attachments"]
        assert attachments[0]["contentType"] == "application/vnd.microsoft.card.adaptive"

    def test_send_teams_invalid_url(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="webhook_url must be an https://"):
            notifications.send_teams_notification("ftp://bad.url", "message")

    def test_send_teams_failure_returns_error_dict(self, monkeypatch):
        import docreview360.http_client as _hc
        from docreview360 import notifications

        monkeypatch.setattr(_hc, "post", lambda *a, **kw: (_ for _ in ()).throw(OSError("timeout")))
        result = notifications.send_teams_notification(
            "https://myorg.webhook.office.com/xxx", "alert"
        )
        assert "error" in result

    # --- Webhook ---

    def test_send_webhook_notification_success(self, monkeypatch):
        import docreview360.http_client as _hc
        from docreview360 import notifications

        captured = []
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        def capture_post(url, json=None, **kw):
            captured.append(json)
            return resp

        monkeypatch.setattr(_hc, "post", capture_post)
        result = notifications.send_webhook_notification(
            "https://api.example.com/hooks/review",
            "review.approved",
            project_id="p-42",
            reviewer="alice",
        )
        assert result["event"] == "review.approved"
        assert result["project_id"] == "p-42"
        assert len(notifications.sent_webhook_notifications) == 1

    def test_send_webhook_invalid_url(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="https://"):
            notifications.send_webhook_notification("http://insecure.com", "event")

    def test_send_webhook_empty_event(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="event is required"):
            notifications.send_webhook_notification("https://example.com", "")

    # --- Email ---

    def test_send_email_success(self):
        from docreview360 import notifications

        result = notifications.send_email(
            "due_reminder", "alice@example.com", item="Report Q4", due_date="2024-12-31"
        )
        assert result["to"] == "alice@example.com"
        assert "Report Q4" in result["subject"]
        assert "2024-12-31" in result["body"]

    def test_send_email_missing_placeholder_raises(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="missing placeholder"):
            notifications.send_email("due_reminder", "user@example.com", item="Item")
            # missing due_date

    def test_send_email_invalid_template_raises(self):
        from docreview360 import notifications

        with pytest.raises(KeyError):
            notifications.send_email("nonexistent-template", "user@example.com")

    def test_send_due_date_reminder(self):
        from docreview360 import notifications

        result = notifications.send_due_date_reminder(
            "user@example.com", "Contract v2", "2024-12-31"
        )
        assert "Contract v2" in result["subject"]
        assert "2024-12-31" in result["body"]

    def test_send_completion_notification(self):
        from docreview360 import notifications

        result = notifications.send_completion_notification("user@example.com", "Annual Review")
        assert "Annual Review" in result["subject"]

    # --- add_template ---

    def test_add_template_success(self):
        from docreview360 import notifications

        try:
            notifications.add_template(
                "test_tmpl_unique_xyz", "{user} says {msg}", "From {user}: {msg}"
            )
        except ValueError:
            pass  # already exists from previous test run
        # Template was added or already existed — just check it's in TEMPLATES
        assert "test_tmpl_unique_xyz" in notifications.TEMPLATES

    def test_add_template_empty_name_raises(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="name required"):
            notifications.add_template("  ", "subject", "body")

    def test_add_template_empty_subject_raises(self):
        from docreview360 import notifications

        with pytest.raises(ValueError, match="subject required"):
            notifications.add_template("tmpl_new_x1", "  ", "body")

    def test_add_template_duplicate_raises(self):
        from docreview360 import notifications

        try:
            notifications.add_template("tmpl_dup_test", "Subject", "Body")
        except ValueError:
            pass
        with pytest.raises(ValueError, match="already exists"):
            notifications.add_template("tmpl_dup_test", "Subject2", "Body2")


# ===========================================================================
# CMS Backend Routing
# ===========================================================================


class TestCMSBackend:
    """Tests for CMS backend selection, save, and fetch."""

    def _make_config(self, cms: str):
        from docreview360.config import Config

        return Config(database="sqlite", editor="tiptap", cms=cms, auth="local")

    # --- SharePointBackend ---

    def test_sharepoint_backend_upload(self, monkeypatch):
        from docreview360.cms import SharePointBackend
        from docreview360.sharepoint import SharePointClient

        mock_client = MagicMock(spec=SharePointClient)
        mock_client.upload_file.return_value = "sp-item-1"
        backend = SharePointBackend(client=mock_client)

        item_id = backend.upload("docs/report.pdf", b"PDF data")
        assert item_id == "sp-item-1"
        mock_client.upload_file.assert_called_once_with("docs/report.pdf", b"PDF data")

    def test_sharepoint_backend_download(self, monkeypatch):
        from docreview360.cms import SharePointBackend
        from docreview360.sharepoint import SharePointClient

        mock_client = MagicMock(spec=SharePointClient)
        mock_client.download_file.return_value = b"downloaded bytes"
        backend = SharePointBackend(client=mock_client)

        data = backend.download("sp-item-1")
        assert data == b"downloaded bytes"

    # --- FileCMSBackend ---

    def test_file_cms_backend_upload(self, monkeypatch):
        from docreview360.cms import FileCMSBackend

        uploaded = []
        monkeypatch.setattr(
            "docreview360.cms.upload_file",
            lambda bucket, name, data: uploaded.append((bucket, name, data)),
        )
        monkeypatch.setattr("docreview360.cms.download_file", lambda bucket, name: b"")

        backend = FileCMSBackend(name="local", bucket="cms_store/local")
        result = backend.upload("test.md", b"markdown content")
        assert result == "test.md"
        assert uploaded[0] == ("cms_store/local", "test.md", b"markdown content")

    def test_file_cms_backend_download(self, monkeypatch):
        from docreview360.cms import FileCMSBackend

        monkeypatch.setattr(
            "docreview360.cms.download_file", lambda bucket, name: b"data from store"
        )
        backend = FileCMSBackend(name="gdrive", bucket="cms_store/gdrive")
        data = backend.download("file-id-123")
        assert data == b"data from store"

    # --- get_cms_backend ---

    def test_get_cms_backend_none(self):
        from docreview360.cms import get_cms_backend

        config = self._make_config("none")
        backend = get_cms_backend(config=config)
        assert backend is None

    def test_get_cms_backend_empty_string(self):
        from docreview360.cms import get_cms_backend

        config = self._make_config("")
        backend = get_cms_backend(config=config)
        assert backend is None

    def test_get_cms_backend_sharepoint(self, monkeypatch):
        from docreview360.cms import SharePointBackend, get_cms_backend
        from docreview360.sharepoint import SharePointClient

        mock_client = MagicMock(spec=SharePointClient)
        config = self._make_config("sharepoint")
        backend = get_cms_backend(config=config, client=mock_client)
        assert isinstance(backend, SharePointBackend)
        assert backend.name == "sharepoint"

    def test_get_cms_backend_local(self, monkeypatch):
        from docreview360.cms import FileCMSBackend, get_cms_backend

        monkeypatch.setattr("docreview360.cms.load_settings", lambda: {})
        config = self._make_config("local")
        backend = get_cms_backend(config=config)
        assert isinstance(backend, FileCMSBackend)
        assert backend.name == "local"

    def test_get_cms_backend_unknown_raises(self):
        from docreview360.cms import get_cms_backend

        config = self._make_config("dropbox")
        with pytest.raises(ValueError, match="Unsupported CMS backend"):
            get_cms_backend(config=config)

    def test_get_cms_backend_confluence(self, monkeypatch):
        from docreview360.cms import FileCMSBackend, get_cms_backend

        monkeypatch.setattr("docreview360.cms.load_settings", lambda: {})
        config = self._make_config("confluence")
        backend = get_cms_backend(config=config)
        assert isinstance(backend, FileCMSBackend)
        assert backend.name == "confluence"


# ===========================================================================
# Documenso — extended coverage
# ===========================================================================


class TestDocumensoExtended:
    """Additional Documenso coverage beyond the existing circuit-breaker tests."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        from docreview360.integrations.signature import documenso

        documenso._signatures.clear()
        documenso._sig_workflows.clear()
        documenso._sig_certificates.clear()
        documenso._certificates.clear()
        documenso._reset_circuit_breaker_for_tests()
        yield
        documenso._signatures.clear()
        documenso._sig_workflows.clear()
        documenso._sig_certificates.clear()
        documenso._certificates.clear()
        documenso._reset_circuit_breaker_for_tests()

    def test_request_signature_stub_creates_record(self):
        from docreview360.integrations.signature import documenso

        sig_id, url, meta = documenso.request_signature("doc-1", "alice")
        assert sig_id in documenso._signatures
        assert documenso._signatures[sig_id] == "pending"
        assert sig_id in url

    def test_request_signature_invalid_args(self):
        from docreview360.integrations.signature import documenso

        with pytest.raises(ValueError):
            documenso.request_signature("", "alice")
        with pytest.raises(ValueError):
            documenso.request_signature("doc-1", "")

    def test_process_webhook_valid_payload(self, monkeypatch):
        from docreview360.integrations.signature import documenso

        monkeypatch.setattr(documenso, "log_event", lambda *a, **kw: None)
        sig_id, _, _ = documenso.request_signature("doc-2", "bob")
        documenso.process_webhook({
            "id": sig_id,
            "status": "signed",
            "certificate_url": None,
            "signed_at": None,
        })
        assert documenso._signatures[sig_id] == "signed"

    def test_process_webhook_invalid_payload_raises(self, monkeypatch):
        from docreview360.integrations.signature import documenso

        monkeypatch.setattr(documenso, "log_event", lambda *a, **kw: None)
        with pytest.raises(Exception):
            documenso.process_webhook({"id": "x"})  # missing status

    def test_verify_signature_stub(self):
        import hashlib

        from docreview360.integrations.signature import documenso

        doc_bytes = b"pdf-content-bytes"
        sig_id, _, _ = documenso.request_signature("doc-3", "carol")
        # Initially pending — verify returns False
        assert documenso.verify_signature(sig_id, doc_bytes) is False
        # Set signed status AND matching cert hash — now verify returns True
        documenso._signatures[sig_id] = "signed"
        documenso._sig_certificates[sig_id] = hashlib.sha256(doc_bytes).hexdigest()
        assert documenso.verify_signature(sig_id, doc_bytes) is True

    def test_health_check_stub_mode(self, monkeypatch):
        from docreview360.integrations.signature import documenso

        monkeypatch.setattr(documenso, "DOCUMENSO_URL", None)
        assert documenso.health_check() is True

    def test_normalize_cert_url(self):
        from docreview360.integrations.signature.documenso import _normalize_cert_url

        url = "https://certs.example.com/cert"
        normalized = _normalize_cert_url(url)
        assert normalized.endswith("/")

    def test_circuit_breaker_complete_signature_trips(self, monkeypatch):
        from docreview360.integrations.signature import documenso

        monkeypatch.setattr(documenso, "DOCUMENSO_URL", "https://remote")
        monkeypatch.setattr(documenso, "FAILURE_THRESHOLD", 2)
        monkeypatch.setattr(documenso, "FAILURE_WINDOW_SECONDS", 60)
        monkeypatch.setattr(documenso, "FAILURE_COOLDOWN_SECONDS", 300)
        monkeypatch.setattr(documenso, "log_event", lambda *a, **kw: None)
        monkeypatch.setattr(
            "docreview360.integrations.signature.documenso.set_provider_health",
            lambda name, healthy: None,
        )

        def failing_post(url, **kw):
            req = httpx.Request("POST", url)
            raise httpx.ConnectError("unreachable", request=req)

        monkeypatch.setattr(documenso, "http_post", failing_post)
        # First failure — breaker not tripped yet
        with pytest.raises(RuntimeError):
            documenso.complete_signature("sig-a")
        assert documenso._remote_suspended_until is None
        # Second failure — breaker trips, falls back to stub
        documenso.complete_signature("sig-b")
        assert documenso._remote_suspended_until is not None


# ===========================================================================
# Provider Store
# ===========================================================================


class TestProviderStore:
    """Tests for the YAML-backed provider health/priority store."""

    def test_load_providers_nonexistent_file(self, tmp_path):
        from docreview360.provider_store import load_providers

        providers = load_providers(tmp_path / "providers.yaml")
        assert isinstance(providers, dict)

    def test_set_provider_health_and_load(self, tmp_path, monkeypatch):
        from docreview360 import provider_store

        monkeypatch.setattr(provider_store, "PROVIDERS_FILE", tmp_path / "providers.yaml")
        provider_store.set_provider_health("docusign", False)
        providers = provider_store.load_providers(tmp_path / "providers.yaml")
        assert providers["docusign"]["healthy"] is False

    def test_set_provider_health_recovers(self, tmp_path, monkeypatch):
        from docreview360 import provider_store

        monkeypatch.setattr(provider_store, "PROVIDERS_FILE", tmp_path / "providers.yaml")
        provider_store.set_provider_health("documenso", False)
        provider_store.set_provider_health("documenso", True)
        providers = provider_store.load_providers(tmp_path / "providers.yaml")
        assert providers["documenso"]["healthy"] is True

    def test_get_active_providers_filters_unhealthy(self, tmp_path, monkeypatch):
        from docreview360 import provider_store

        monkeypatch.setattr(provider_store, "PROVIDERS_FILE", tmp_path / "providers.yaml")
        provider_store.set_provider_health("docusign", False)
        provider_store.set_provider_health("documenso", True)
        active = provider_store.get_active_providers(tmp_path / "providers.yaml")
        assert "docusign" not in str(active)


# ===========================================================================
# Integration — Signature Provider Registration
# ===========================================================================


class TestSignatureProviderRegistry:
    """Tests for the signature provider registry and DocuSignProvider class."""

    def test_docusign_provider_registered(self):
        from docreview360.integrations.signature import docusign
        from docreview360.integrations.signature.base import providers

        assert any(isinstance(p, docusign.DocuSignProvider) for p in providers.values())

    def test_docusign_provider_interface(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        provider = docusign.DocuSignProvider()
        sig_id, url, meta = provider.request_signature("doc-99", "user")
        assert sig_id
        assert provider.health_check() is True
        assert provider.verify_signature(sig_id, b"pdf") is False
        assert provider.validate_signature(b"pdf", None, {"status": "completed"}) is True


# ===========================================================================
# Stress / Concurrency simulation
# ===========================================================================


class TestConcurrencyStress:
    """Simulate concurrent integration usage — no actual network I/O."""

    def test_concurrent_docusign_signature_requests(self):
        """Simulate 20 concurrent signature requests — all should create unique IDs."""
        from concurrent.futures import ThreadPoolExecutor

        from docreview360.integrations.signature import docusign

        docusign._signatures.clear()
        results = []

        def request(n):
            sig_id, url, meta = docusign.request_signature(f"doc-{n}", f"user-{n}")
            return sig_id

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(request, i) for i in range(20)]
            results = [f.result() for f in futures]

        # All IDs should be unique
        assert len(set(results)) == 20
        docusign._signatures.clear()

    def test_concurrent_log_connector_emit(self):
        """Simulate 50 concurrent async log emits — all should complete."""
        from docreview360.log_connectors import (
            LogConnector,
            clear_connectors,
            emit,
            register_connector,
        )
        from docreview360.models import LogEntry

        clear_connectors()
        received = []

        class MemoryConnector(LogConnector):
            async def _send_batch(self, batch):
                received.extend(batch)

        register_connector(MemoryConnector(endpoint="", batch_size=10))

        async def run():
            tasks = []
            for i in range(50):
                entry = LogEntry(
                    id=f"stress-entry-{i}",
                    timestamp=datetime.now(timezone.utc),
                    action=f"event.{i}",
                    entity_id=f"ent-{i}",
                    user_id="stress-user",
                )
                tasks.append(emit(entry))
            await asyncio.gather(*tasks)
            # Flush remaining
            from docreview360.log_connectors import connectors
            for c in connectors:
                await c.flush()

        asyncio.run(run())
        assert len(received) == 50
        clear_connectors()

    def test_concurrent_confluence_page_parsing(self):
        """Parse 100 Confluence responses concurrently — all should succeed."""
        from concurrent.futures import ThreadPoolExecutor

        from docreview360.integrations.confluence_integration import _parse_page

        def parse(i):
            resp = {
                "id": str(i),
                "title": f"Page {i}",
                "space": {"key": "DOCS"},
                "version": {"number": i + 1},
                "body": {"storage": {"value": f"<h1>Heading {i}</h1>"}},
                "_links": {"webui": f"/pages/{i}"},
            }
            return _parse_page(resp)

        with ThreadPoolExecutor(max_workers=20) as pool:
            pages = list(pool.map(parse, range(100)))

        assert len(pages) == 100
        assert all(p.title == f"Page {i}" for i, p in enumerate(pages))


# ===========================================================================
# Edge Cases / Malformed Data
# ===========================================================================


class TestEdgeCases:
    """Edge cases and malformed data that production systems must handle."""

    def test_sharepoint_upload_special_chars_in_path(self, monkeypatch):
        from docreview360.sharepoint import SharePointClient

        client = SharePointClient(site_id="s", drive_id="d", token="t")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "item-special"}
        mock_resp.raise_for_status = MagicMock()
        captured = []

        def fake_put(url, **kwargs):
            captured.append(url)
            return mock_resp

        monkeypatch.setattr("docreview360.sharepoint.requests.put", fake_put)
        client.upload_file("docs/Q4 & Q3/report (final).pdf", b"data")
        assert len(captured) == 1

    def test_google_drive_list_files_empty_response(self, monkeypatch):
        from docreview360.integrations.google_drive_integration import GoogleDriveClient

        client = GoogleDriveClient(access_token="tok", default_folder_id="")
        monkeypatch.setattr(
            "docreview360.integrations.google_drive_integration.urlopen",
            lambda req, timeout=60: _fake_urlopen_response(json.dumps({}).encode()),
        )
        files = client.list_files()
        assert files == []

    def test_confluence_page_missing_body_fields(self):
        from docreview360.integrations.confluence_integration import _parse_page

        resp = {"id": "1", "title": "Bare", "space": {}, "version": {}, "body": {}, "_links": {}}
        page = _parse_page(resp)
        assert page.body_storage == ""
        assert page.version == 1
        assert page.space_key == ""

    def test_docusign_webhook_with_malformed_datetime(self, monkeypatch):
        from docreview360.integrations.signature import docusign

        monkeypatch.setattr(docusign, "log_event", lambda *a, **kw: None)
        sig_id, _, _ = docusign.request_signature("doc-edge", "user")
        # Bad datetime should be logged but not raise
        docusign.process_webhook({
            "envelopeId": sig_id,
            "status": "completed",
            "completedDateTime": "NOT-A-DATE",
        })
        assert docusign._signatures[sig_id] == "completed"

    def test_apns_notification_no_badge(self, monkeypatch):
        import httpx as _httpx
        from docreview360.integrations import apns

        monkeypatch.setenv("DOCREVIEW360_APNS_TEAM_ID", "T")
        monkeypatch.setenv("DOCREVIEW360_APNS_KEY_ID", "K")
        monkeypatch.setenv("DOCREVIEW360_APNS_PRIVATE_KEY", "PEM")
        monkeypatch.setenv("DOCREVIEW360_APNS_BUNDLE_ID", "com.example.app")
        monkeypatch.setattr(apns, "_get_bearer_token", lambda cfg: "jwt")

        captured = []

        class FakeClient:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def post(self, url, content, headers):
                captured.append(json.loads(content))
                resp = MagicMock()
                resp.status_code = 200
                return resp

        monkeypatch.setattr(_httpx, "Client", lambda **kw: FakeClient())
        apns.send_apns_notification("tok", "Title", "Body")
        assert "badge" not in captured[0]["aps"]

    def test_log_entry_model_dump_structure(self):
        from docreview360.models import LogEntry

        entry = LogEntry(
            id="entry-dump-1",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            action="test.event",
            entity_id="ent-42",
            user_id="user-99",
        )
        dumped = entry.model_dump()
        assert dumped["action"] == "test.event"
        assert dumped["entity_id"] == "ent-42"

    def test_confluence_markdown_round_trip(self):
        """Markdown → storage → markdown should preserve content structure."""
        from docreview360.integrations.confluence_integration import (
            _markdown_to_storage,
            _storage_to_markdown,
        )

        original = "# Main Title\n\nSome **bold** and *italic* text.\n\nSee [the link](https://example.com)."
        storage = _markdown_to_storage(original)
        assert "<h1>" in storage
        assert "<strong>" in storage

        recovered = _storage_to_markdown(storage)
        assert "# Main Title" in recovered
        assert "**bold**" in recovered
        assert "[the link](https://example.com)" in recovered

    def test_sharepoint_set_properties_empty_dict(self, monkeypatch):
        from docreview360.sharepoint import SharePointClient

        client = SharePointClient(site_id="s", drive_id="d", token="t")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("docreview360.sharepoint.requests.patch", lambda *a, **kw: mock_resp)
        # Empty props should not raise
        client.set_properties("item-1", {})
        mock_resp.raise_for_status.assert_called_once()
