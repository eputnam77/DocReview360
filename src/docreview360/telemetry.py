# SPDX-License-Identifier: MIT
"""OpenTelemetry tracing integration for DocReview360.

Provides a thin wrapper around OpenTelemetry that degrades gracefully when the
``opentelemetry-sdk`` package is not installed.  In that case all tracing calls
return no-op objects so the rest of the application is unaffected.

Configuration::

    DOCREVIEW360_OTEL_ENABLED=1
    DOCREVIEW360_OTEL_SERVICE_NAME=docreview360
    DOCREVIEW360_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

Optional dependency::

    pip install ".[otel]"
    # or individually:
    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc

Usage::

    from docreview360.telemetry import setup_telemetry, get_tracer

    setup_telemetry()           # call once at application startup

    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("my-operation") as span:
        span.set_attribute("doc.id", doc_id)
        ...
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_SERVICE_NAME = os.environ.get("DOCREVIEW360_OTEL_SERVICE_NAME", "docreview360")
_OTLP_ENDPOINT = os.environ.get(
    "DOCREVIEW360_OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
_ENABLED = os.environ.get("DOCREVIEW360_OTEL_ENABLED", "0").lower() in {"1", "true", "yes"}

_tracer_provider: Any = None
_setup_done = False


class _NoopSpan:
    """Minimal no-op span used when OpenTelemetry is unavailable."""

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def record_exception(self, exc: Exception) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoopTracer:
    """Minimal no-op tracer used when OpenTelemetry is unavailable."""

    def start_as_current_span(self, name: str, **_: Any) -> _NoopSpan:  # type: ignore[override]
        return _NoopSpan()

    def start_span(self, name: str, **_: Any) -> _NoopSpan:
        return _NoopSpan()


def setup_telemetry(
    service_name: str = _SERVICE_NAME,
    otlp_endpoint: str = _OTLP_ENDPOINT,
    *,
    force: bool = False,
) -> bool:
    """Initialise the OpenTelemetry SDK and OTLP exporter.

    Returns True when tracing was successfully configured, False when it was
    skipped (disabled or package unavailable).  Safe to call multiple times.
    """
    global _tracer_provider, _setup_done

    if _setup_done and not force:
        return _tracer_provider is not None

    _setup_done = True

    if not _ENABLED and not force:
        log.debug("telemetry: DOCREVIEW360_OTEL_ENABLED not set; tracing disabled")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer_provider = provider
        log.info(
            "telemetry: OpenTelemetry configured (service=%s, endpoint=%s)",
            service_name,
            otlp_endpoint,
        )
        return True
    except ImportError:
        log.debug(
            "telemetry: opentelemetry-sdk not installed; "
            "install 'docreview360[otel]' to enable tracing"
        )
        return False
    except Exception as exc:
        log.warning("telemetry: failed to configure OpenTelemetry: %s", exc)
        return False


def get_tracer(name: str) -> Any:
    """Return an OpenTelemetry tracer (or a no-op tracer when unavailable).

    *name* should be the ``__name__`` of the calling module.
    """
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        return provider.get_tracer(name)
    except ImportError:
        return _NoopTracer()
    except Exception:
        return _NoopTracer()


def reset_for_testing() -> None:
    """Reset telemetry state. For use in tests only."""
    global _tracer_provider, _setup_done
    _tracer_provider = None
    _setup_done = False
