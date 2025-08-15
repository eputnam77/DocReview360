from __future__ import annotations

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

    def fake_put(url: str, headers, data: bytes) -> DummyResponse:
        uploaded.append((url, data))
        return DummyResponse(json_data={"id": "x"})

    def fake_patch(url: str, headers, json) -> DummyResponse:
        patched.append((url, json))
        return DummyResponse()

    def fake_get(url: str) -> DummyResponse:
        assert url == "http://cert"
        return DummyResponse(content=b"cert-data")

    monkeypatch.setattr("docreview360.sharepoint.requests.put", fake_put)
    monkeypatch.setattr("docreview360.sharepoint.requests.patch", fake_patch)
    monkeypatch.setattr("docreview360.approvals.requests.get", fake_get)

    document = b"hello"
    approval = create_approval("wf1", "bob", "doc1", document=document)
    signed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    update_approval_state(
        approval.id,
        "approved",
        document=document,
        certificate_url="http://cert",
        signed_at=signed_at,
    )

    assert len(uploaded) == 2
    assert patched
    props = patched[0][1]
    assert props["certificateUrl"] == "http://cert"
    assert props["documentHash"] == hashlib.sha256(document).hexdigest()
    assert props["signedDate"].startswith("2024-01-01")
