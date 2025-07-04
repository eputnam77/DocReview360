"""Basic observability helpers for DocuFlow.

The module exposes a minimal API to start a Prometheus metrics server and to
enable Sentry error reporting.  These utilities keep the implementation light so
that tests do not require any external services.
"""

from __future__ import annotations

import os
from typing import Dict

import sentry_sdk
from prometheus_client import Counter, start_http_server

REQUEST_COUNTER = Counter(
    "docuflow_requests_total", "Number of HTTP requests processed by DocuFlow"
)


def init_observability(port: int | None = None, *, dsn: str | None = None) -> Dict[str, str]:
    """Initialise Prometheus metrics and optional Sentry reporting."""

    services: Dict[str, str] = {}

    if port is not None:
        if port <= 0 or port >= 65536:
            raise ValueError("port must be between 1 and 65535")
        start_http_server(port)
        services["prometheus"] = f"http://localhost:{port}/"

    dsn = dsn or os.getenv("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(dsn=dsn, traces_sample_rate=1.0)
        services["sentry"] = "enabled"

    return services


def open_dashboard() -> str:
    """Return URL to the monitoring dashboard."""
    return "http://localhost:8000/langgraph"
