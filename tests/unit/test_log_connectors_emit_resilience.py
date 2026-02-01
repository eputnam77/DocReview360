from __future__ import annotations

from datetime import datetime, timezone

import pytest

from docreview360.log_connectors import LogConnector, clear_connectors, emit, register_connector
from docreview360.models import LogEntry


class RecordingConnector(LogConnector):
    def __init__(self) -> None:
        super().__init__(endpoint="record", batch_size=1)
        self.batches: list[list[dict[str, object]]] = []

    async def _send_batch(self, batch: list[dict[str, object]]) -> None:
        self.batches.append(batch)


class FailingConnector(LogConnector):
    def __init__(self) -> None:
        super().__init__(endpoint="fail", batch_size=1)

    async def _send_batch(self, batch: list[dict[str, object]]) -> None:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_emit_continues_after_connector_failure() -> None:
    clear_connectors()
    recorder = RecordingConnector()
    register_connector(FailingConnector())
    register_connector(recorder)
    entry = LogEntry(
        id="log-1",
        timestamp=datetime.now(timezone.utc),
        action="created",
    )

    await emit(entry)

    assert len(recorder.batches) == 1
    assert recorder.batches[0][0]["action"] == "created"
    clear_connectors()
