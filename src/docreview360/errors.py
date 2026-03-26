# SPDX-License-Identifier: MIT
"""Unified error response contract for DocReview360.

All API errors are serialised as an ``ErrorResponse`` envelope so clients have
a stable shape to parse regardless of which router raised the error.

Shape::

    {
        "error": "not_found",
        "message": "Project abc not found",
        "trace_id": "3f2a...",
        "status_code": 404
    }

Usage in routers::

    from docreview360.errors import AppError, NotFoundError, raise_http

    raise NotFoundError("Project", project_id)
    # or:
    raise_http(404, "custom message", code="custom_code")
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Wire format
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all 4xx/5xx responses."""

    error: str
    message: str
    trace_id: str
    status_code: int
    details: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Application exception hierarchy
# ---------------------------------------------------------------------------


class AppError(Exception):
    """Base class for all application-level errors.

    Subclasses set ``status_code`` and ``error`` at the class level so callers
    can ``raise SomeError("human readable message")`` without repeating HTTP
    status codes throughout the codebase.
    """

    status_code: int = 500
    error: str = "internal_error"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        *,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        self.trace_id = trace_id or uuid.uuid4().hex

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error=self.error,
            message=self.message,
            trace_id=self.trace_id,
            status_code=self.status_code,
            details=self.details,
        )

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_response().model_dump(),
        )


class NotFoundError(AppError):
    status_code = 404
    error = "not_found"

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str | int | None = None,
        **kwargs: Any,
    ) -> None:
        name = f"{resource} {identifier!r}" if identifier is not None else resource
        super().__init__(f"{name} not found", **kwargs)


class ConflictError(AppError):
    status_code = 409
    error = "conflict"


class ValidationError(AppError):
    status_code = 422
    error = "validation_error"


class AuthenticationError(AppError):
    status_code = 401
    error = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    error = "forbidden"


class RateLimitError(AppError):
    status_code = 429
    error = "rate_limit_exceeded"

    def __init__(self, message: str = "Rate limit exceeded", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class ServiceUnavailableError(AppError):
    status_code = 503
    error = "service_unavailable"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def raise_http(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> None:
    """Raise an ``HTTPException`` with a structured ``ErrorResponse`` detail."""
    _trace_id = trace_id or uuid.uuid4().hex
    _code = code or _default_code(status_code)
    payload = ErrorResponse(
        error=_code,
        message=message,
        trace_id=_trace_id,
        status_code=status_code,
        details=details,
    )
    raise HTTPException(status_code=status_code, detail=payload.model_dump())


def _default_code(status_code: int) -> str:
    _map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
        503: "service_unavailable",
    }
    return _map.get(status_code, "error")


def error_json_response(exc: AppError) -> JSONResponse:
    """Convert an ``AppError`` directly to a ``JSONResponse``."""
    resp = exc.to_response()
    return JSONResponse(status_code=exc.status_code, content=resp.model_dump())
