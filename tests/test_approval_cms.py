from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone

from docreview360.approvals import create_approval, update_approval_state


class DummyResponse:
    def __init__(self, *, json_data=None, content: bytes = b"") -> None:
        self._json = json_data or {}
        self.content = content

    def raise_for_status(self) -> None:  # pragma: no cover - no http
        return None

    def json(self):  # pragma: no cover - no http
        return self._json


def test_update_state_uploads_to_cms(monkeypatch):
    monkeypatch.setenv("SHAREPOINT_SITE_ID", "s")
    monkeypatch.setenv("SHAREPOINT_DRIVE_ID", "d")
    monkeypatch.setenv("SHAREPOINT_TOKEN", "t")

    uploaded = []
    patched = []

    def fake_put(url: str, headers, data: bytes, timeout: float) -> DummyResponse:
        uploaded.append((url, data))
        assert timeout > 0
        return DummyResponse(json_data={"id": "x"})

    def fake_patch(url: str, headers, json, timeout: float) -> DummyResponse:
        patched.append((url, json))
        assert timeout > 0
        return DummyResponse()

    def fake_fetch(url: str) -> bytes:
        assert url == "https://cert"
        return b"cert-data"

    monkeypatch.setattr("docreview360.sharepoint.requests.put", fake_put)
    monkeypatch.setattr("docreview360.sharepoint.requests.patch", fake_patch)
    monkeypatch.setattr("docreview360.approvals.fetch_certificate", fake_fetch)

    document = b"hello"
    approval = create_approval("wf1", "bob", "doc1", document=document)
    signed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    asyncio.run(
        update_approval_state(
            approval.id,
            "approved",
            document=document,
            certificate_url="https://cert",
            signed_at=signed_at,
        )
    )

    assert len(uploaded) == 2
    assert patched
    props = patched[0][1]
    assert props["certificateUrl"] == "https://cert"
    assert props["documentHash"] == hashlib.sha256(document).hexdigest()
    assert props["signedDate"].startswith("2024-01-01")
