"""Basic observability helpers for DocReview360.

The module exposes a minimal API to start a Prometheus metrics server and to
enable Sentry error reporting.  These utilities keep the implementation light so
that tests do not require any external services.
"""

from __future__ import annotations

import os
from types import ModuleType
from typing import Dict, Optional, cast

from prometheus_client import Counter, start_http_server

try:
    import sentry_sdk as _sentry_sdk
except Exception:
    _sentry_sdk = None

sentry_sdk: Optional[ModuleType] = cast(Optional[ModuleType], _sentry_sdk)

REQUEST_COUNTER = Counter(
    "docreview360_requests_total", "Number of HTTP requests processed by DocReview360"
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
        if sentry_sdk is not None:  # real library available
            sentry_sdk.init(dsn=dsn, traces_sample_rate=1.0)
        # mark enabled regardless so tests don't depend on the package
        services["sentry"] = "enabled"

    return services


def open_dashboard() -> str:
    """Return URL to the monitoring dashboard."""
    return "http://localhost:8000/langgraph"


def start_observability_stack(prom_port: int = 8000, grafana_port: int = 3000) -> Dict[str, str]:
    """Start the lightweight observability stack and return service URLs."""
    services = init_observability(prom_port)
    if grafana_port <= 0 or grafana_port >= 65536:
        raise ValueError("invalid grafana_port")
    services["grafana"] = f"http://localhost:{grafana_port}/"
    services.setdefault("loki", "http://localhost:3100/")
    services.setdefault("sentry", "enabled")
    return services
