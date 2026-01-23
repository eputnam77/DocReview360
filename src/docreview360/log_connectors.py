"""Adapters for streaming or batching log entries to external services."""

from __future__ import annotations

import asyncio
import time
from typing import Any, List

import httpx

from .models import LogEntry

try:  # pragma: no cover - optional dependency
    import boto3  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - used in CloudWatchConnector only
    boto3 = None


class LogConnector:
    """Base connector supporting simple batching."""

    def __init__(self, endpoint: str, api_key: str | None = None, *, batch_size: int = 1) -> None:
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            raise TypeError("batch_size must be an integer")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.endpoint = endpoint
        self.api_key = api_key
        self.batch_size = batch_size
        self._buffer: List[dict[str, Any]] = []

    async def emit(self, entry: LogEntry) -> None:
        """Queue ``entry`` and flush when batch is full."""
        self._buffer.append(entry.model_dump())
        if len(self._buffer) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        if not self._buffer:
            return
        await self._send_batch(self._buffer)
        self._buffer = []

    async def _send_batch(self, batch: List[dict[str, Any]]) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class ELKConnector(LogConnector):
    """Send log batches to an Elasticsearch/ELK HTTP endpoint."""

    async def _send_batch(self, batch: List[dict[str, Any]]) -> None:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(self.endpoint, json=batch, headers=headers)


class SplunkConnector(LogConnector):
    """Send log batches to Splunk's HTTP Event Collector."""

    async def _send_batch(self, batch: List[dict[str, Any]]) -> None:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Splunk {self.api_key}"
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(self.endpoint, json=batch, headers=headers)


class CloudWatchConnector(LogConnector):
    """Send log batches to AWS CloudWatch Logs."""

    def __init__(self, log_group: str, *, region: str = "us-east-1", **kwargs: Any) -> None:
        super().__init__(endpoint="", api_key=None, **kwargs)
        self.log_group = log_group
        self.region = region
        self._client: Any | None = None

    def _client_instance(self) -> Any:
        if self._client is None:
            if boto3 is None:  # pragma: no cover - defensive
                raise RuntimeError("boto3 is required for CloudWatchConnector")
            self._client = boto3.client("logs", region_name=self.region)
        return self._client

    async def _send_batch(self, batch: List[dict[str, Any]]) -> None:
        client = self._client_instance()
        loop = asyncio.get_running_loop()
        # ``loop.time()`` returns a monotonic clock which is not tied to the
        # Unix epoch. CloudWatch expects timestamps in milliseconds since epoch
        # and using the monotonic clock resulted in values near zero which were
        # rejected or mis-ordered. Use ``time.time()`` to generate proper epoch
        # timestamps.
        events = [{"timestamp": int(time.time() * 1000), "message": str(entry)} for entry in batch]
        await loop.run_in_executor(
            None,
            lambda: client.put_log_events(
                logGroupName=self.log_group,
                logStreamName="docreview360",
                logEvents=events,
            ),
        )


connectors: List[LogConnector] = []


def register_connector(connector: LogConnector) -> None:
    connectors.append(connector)


def clear_connectors() -> None:
    connectors.clear()


emit_lock = asyncio.Lock()


async def emit(entry: LogEntry) -> None:
    """Dispatch ``entry`` to all registered connectors respecting order."""
    async with emit_lock:
        await asyncio.gather(*(c.emit(entry) for c in list(connectors)))


__all__ = [
    "LogConnector",
    "ELKConnector",
    "SplunkConnector",
    "CloudWatchConnector",
    "register_connector",
    "clear_connectors",
    "emit",
]
