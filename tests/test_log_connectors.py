from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import yaml
from _pytest.monkeypatch import MonkeyPatch
from docreview360 import logs
from docreview360.config import Config
from docreview360.log_connectors import (
    CloudWatchConnector,
    ELKConnector,
    clear_connectors,
    register_connector,
)


def test_config_connectors(tmp_path: Path) -> None:
    path = tmp_path / "cfg.yaml"
    data = {
        "database": "sqlite",
        "editor": "vim",
        "cms": "local",
        "auth": "noop",
        "log_connectors": [
            {"type": "elk", "endpoint": "http://elk", "api_key": "k", "batch_size": 2}
        ],
    }
    path.write_text(yaml.safe_dump(data))
    cfg = Config.load(path)
    assert cfg is not None
    assert cfg.log_connectors[0].endpoint == "http://elk"
    cfg.save(path)
    saved = yaml.safe_load(path.read_text())
    assert saved["log_connectors"][0]["api_key"] == "k"


def test_connector_rejects_invalid_batch_size() -> None:
    with pytest.raises(TypeError, match="batch_size"):
        ELKConnector("http://elk", batch_size=1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="batch_size"):
        ELKConnector("http://elk", batch_size=0)


@pytest.mark.asyncio
async def test_elk_connector_batches(monkeypatch: MonkeyPatch) -> None:
    sent: list[list[dict[str, object]]] = []

    import asyncio

    async def fake_post(self, url, json=None, headers=None):  # type: ignore[no-untyped-def]
        sent.append(json)
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    connector = ELKConnector("http://elk", api_key="k", batch_size=2)
    register_connector(connector)

    try:
        logs.log_event("a")
        logs.log_event("b")
        await asyncio.sleep(0.1)
    finally:
        clear_connectors()
        logs.clear_logs()
    assert len(sent) == 1
    assert len(sent[0]) == 2


@pytest.mark.asyncio
async def test_cloudwatch_connector_uses_epoch(monkeypatch: MonkeyPatch) -> None:
    class Dummy:
        def __init__(self) -> None:
            self.events: list[dict[str, object]] | None = None

        def put_log_events(self, *, logGroupName, logStreamName, logEvents):  # type: ignore[no-untyped-def]
            self.events = logEvents

    connector = CloudWatchConnector("group")
    connector._client = Dummy()  # type: ignore[assignment]
    entry = logs.LogEntry(id="1", timestamp=datetime.now(timezone.utc), action="x")
    await connector._send_batch([entry])
    assert connector._client.events is not None  # type: ignore[union-attr]
    ts = connector._client.events[0]["timestamp"]  # type: ignore[index]
    assert ts > 1_000_000_000_000  # milliseconds since Unix epoch
