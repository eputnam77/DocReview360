import sys
import types
from datetime import datetime
from types import SimpleNamespace

import pytest

fake_approvals = types.ModuleType("docreview360.approvals")
fake_approvals.create_approval = lambda *a, **k: None
fake_approvals.submit_draft_for_approval = lambda *a, **k: None
sys.modules.setdefault("docreview360.approvals", fake_approvals)


@pytest.mark.asyncio
async def test_upload_final_pdf_stores_metadata(monkeypatch):
    from docreview360.integrations.sharepoint_upload import upload_final_pdf

    uploaded = {}
    props = {}

    async def fake_upload_file(path: str, data: bytes) -> str:
        uploaded[path] = data
        return "item123"

    async def fake_set_properties(item_id: str, properties: dict[str, str]) -> None:
        props[item_id] = properties

    async def fake_client():
        return SimpleNamespace(upload_file=fake_upload_file, set_properties=fake_set_properties)

    monkeypatch.setattr(
        "docreview360.sharepoint.async_client_from_env",
        lambda: fake_client(),
    )

    ts = datetime(2024, 1, 1)
    metadata = {"transaction_id": "tx42", "timestamp": "2024-01-01T00:00:00Z"}

    await upload_final_pdf(
        approval_id="appr1",
        item_id="doc1",
        document=b"pdfdata",
        document_hash="hash",
        provider_metadata=metadata,
        signed_at=ts,
    )

    assert uploaded == {"signed/appr1": b"pdfdata"}
    assert props["doc1"]["transactionId"] == "tx42"
    assert props["doc1"]["providerTimestamp"] == "2024-01-01T00:00:00Z"
