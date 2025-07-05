import httpx
from httpx import Response

from docuflow.metabase_sync import run_field_sync


def test_run_field_sync(monkeypatch) -> None:
    transport = httpx.MockTransport(lambda r: Response(200, json={"ok": True}))
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(httpx, "post", client.post)
    run_field_sync("https://mb.example", "tkn")
