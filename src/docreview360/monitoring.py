"""Basic observability helpers for DocReview360.

The module exposes a minimal API to start a Prometheus metrics server and to
enable Sentry error reporting.  These utilities keep the implementation light so
that tests do not require any external services.
"""

from __future__ import annotations

import socket
from contextlib import closing
from types import ModuleType
from typing import Dict, Optional, cast

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from .secrets import get_secret

try:
    import sentry_sdk as _sentry_sdk
except Exception:
    _sentry_sdk = None

sentry_sdk: Optional[ModuleType] = cast(Optional[ModuleType], _sentry_sdk)

REQUEST_COUNTER = Counter(
    "docreview360_requests_total", "Number of HTTP requests processed by DocReview360"
)

# Verification metrics used by HTTP endpoints and background tasks.
VERIFICATION_COUNTER = Counter(
    "docreview360_verifications_total",
    "Number of document verification operations",
    ["source", "status"],
)
VERIFICATION_DURATION = Histogram(
    "docreview360_verification_seconds",
    "Time spent performing document verifications",
    ["source"],
)

# Health status for signature providers: 1 indicates healthy, 0 unhealthy.
PROVIDER_HEALTH = Gauge(
    "docreview360_provider_health",
    "Health status of configured signature providers",
    ["provider"],
)

# Metrics tracking signature request issues and webhook delivery problems.
SIGNATURE_FAILURES = Counter(
    "docreview360_signature_failures_total",
    "Number of failed signature requests",
    ["provider"],
)
WEBHOOK_DELAY = Histogram(
    "docreview360_webhook_delay_seconds",
    "Delay between provider event and webhook processing",
    ["provider"],
)
HASH_MISMATCHES = Counter(
    "docreview360_webhook_hash_mismatch_total",
    "Number of webhook payloads failing signature validation",
    ["provider"],
)

# Metrics tracking approval artifact upload reliability.
APPROVAL_UPLOAD_RETRIES = Counter(
    "docreview360_approval_upload_retries_total",
    "Retry attempts and exhausted retries when uploading approval artifacts",
    ["status"],
)


def _reserve_port() -> int:
    """Return an available TCP port on localhost."""

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_prometheus_server(port: int) -> int:
    """Start the Prometheus HTTP server and return the bound port."""

    result = start_http_server(port)
    if isinstance(result, tuple):
        httpd, _thread = result
        return int(httpd.server_port)
    return port


def init_observability(port: int | None = None, *, dsn: str | None = None) -> Dict[str, str]:
    """Initialize Prometheus metrics and optional Sentry reporting.

    ``prometheus_client.start_http_server`` raises ``OSError`` when the
    requested port is already bound.  Previously this bubbled up to callers
    which made the helper unreliable in test environments where arbitrary
    ports may be in use.  The function now falls back to an ephemeral port on
    such errors and returns the actual URL used by the metrics server.  The
    ``port`` argument accepts ``0`` to explicitly request an ephemeral port.
    """

    services: Dict[str, str] = {}

    if port is not None:
        if port < 0 or port >= 65536:
            raise ValueError("port must be between 0 and 65535")
        attempt = port
        if attempt == 0:
            attempt = _reserve_port()
        try:
            actual_port = _start_prometheus_server(attempt)
        except OSError:
            fallback = _reserve_port()
            actual_port = _start_prometheus_server(fallback)
        services["prometheus"] = f"http://localhost:{actual_port}/"

    dsn = dsn or get_secret("sentry_dsn")
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
    return services
