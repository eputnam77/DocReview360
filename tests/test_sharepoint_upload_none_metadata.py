from datetime import datetime

import pytest

from docreview360 import sharepoint
from docreview360.integrations import sharepoint_upload as su


class DummyClient:
    def __init__(self):
        self.uploads = []
        self.props = None

    async def upload_file(self, path, data):
        self.uploads.append((path, data))

    async def set_properties(self, item_id, props):
        self.props = props


@pytest.mark.asyncio
async def test_upload_final_pdf_handles_none_metadata(monkeypatch):
    client = DummyClient()

    async def fake_client_from_env():
        return client

    monkeypatch.setattr(sharepoint, "async_client_from_env", fake_client_from_env)

    await su.upload_final_pdf(
        approval_id="a1",
        item_id="i1",
        document=b"data",
        document_hash="hash",
        provider_metadata=None,
        signed_at=datetime(2024, 1, 1),
    )

    assert client.props["providerTimestamp"] == datetime(2024, 1, 1).isoformat()
