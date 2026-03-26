# SPDX-License-Identifier: MIT
"""Structured JSON logging with correlation IDs for DocReview360.

Provides a :class:`StructuredJsonFormatter` that emits each log record as a
single-line JSON object.  A ``trace_id`` field is injected automatically from
the ``TRACE_ID`` :class:`~contextvars.ContextVar` used by the audit subsystem
so that every log line emitted during a request can be correlated.

Configuration::

    DOCREVIEW360_LOG_LEVEL=INFO
    DOCREVIEW360_LOG_SERVICE=docreview360
    DOCREVIEW360_STRUCTURED_LOGGING=1   # enable (default 0 in dev; 1 in prod)

Usage::

    from docreview360.structured_logging import setup_structured_logging
    setup_structured_logging()
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

_SERVICE = os.environ.get("DOCREVIEW360_LOG_SERVICE", "docreview360")
_LEVEL = os.environ.get("DOCREVIEW360_LOG_LEVEL", "INFO").upper()
_ENABLED = os.environ.get("DOCREVIEW360_STRUCTURED_LOGGING", "0").lower() in {"1", "true", "yes"}


def _get_trace_id() -> str | None:
    """Return the current trace/correlation ID from the context variable."""
    try:
        from .logs._db import TRACE_ID

        return TRACE_ID.get(None)
    except Exception:
        return None


class StructuredJsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Fields emitted:
      - ``timestamp``   ISO-8601 UTC
      - ``level``       log level name
      - ``logger``      logger name
      - ``message``     formatted message
      - ``service``     service name (``DOCREVIEW360_LOG_SERVICE``)
      - ``trace_id``    correlation ID from the request context (if set)
      - ``exc_info``    exception traceback (only when an exception is attached)
      - ``extra``       any additional ``extra={}`` fields passed to the logger
    """

    def __init__(self, service: str = _SERVICE) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "service": self.service,
        }
        trace_id = _get_trace_id()
        if trace_id:
            data["trace_id"] = trace_id

        # Include any fields added via extra={...}.
        _skip = frozenset(logging.LogRecord.__dict__) | {
            "message",
            "asctime",
            "args",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "taskName",
            "thread",
            "threadName",
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in _skip}
        if extra:
            data["extra"] = extra

        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        elif record.exc_text:
            data["exc_info"] = record.exc_text

        return json.dumps(data, default=str)


def setup_structured_logging(
    level: str = _LEVEL,
    service: str = _SERVICE,
    *,
    force: bool = False,
) -> None:
    """Configure the root logger to emit structured JSON.

    Installs a :class:`StructuredJsonFormatter` on the root logger's
    ``StreamHandler``.  Calling this function is a no-op when
    ``DOCREVIEW360_STRUCTURED_LOGGING`` is not set, unless *force=True*.
    """
    if not _ENABLED and not force:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    # Replace or add a StreamHandler with the JSON formatter.
    formatter = StructuredJsonFormatter(service=service)
    stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
    if stream_handlers:
        for h in stream_handlers:
            h.setFormatter(formatter)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)

    logging.getLogger(__name__).debug(
        "structured JSON logging enabled",
        extra={"service": service, "level": level},
    )
