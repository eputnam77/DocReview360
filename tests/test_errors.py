# SPDX-License-Identifier: MIT
"""Tests for docreview360.errors — unified error response contract."""

from __future__ import annotations

import pytest
from docreview360.errors import (
    AppError,
    AuthenticationError,
    ConflictError,
    ErrorResponse,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    _default_code,
    raise_http,
)
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# ErrorResponse model
# ---------------------------------------------------------------------------


def test_error_response_fields() -> None:
    resp = ErrorResponse(
        error="not_found",
        message="Item not found",
        trace_id="abc123",
        status_code=404,
    )
    assert resp.error == "not_found"
    assert resp.message == "Item not found"
    assert resp.trace_id == "abc123"
    assert resp.status_code == 404
    assert resp.details is None


def test_error_response_with_details() -> None:
    resp = ErrorResponse(
        error="validation_error",
        message="Bad input",
        trace_id="x",
        status_code=422,
        details={"field": "name", "issue": "required"},
    )
    assert resp.details == {"field": "name", "issue": "required"}


# ---------------------------------------------------------------------------
# AppError hierarchy
# ---------------------------------------------------------------------------


def test_app_error_defaults() -> None:
    err = AppError("something broke")
    assert err.status_code == 500
    assert err.error == "internal_error"
    assert err.message == "something broke"
    assert err.trace_id  # auto-generated


def test_app_error_to_response() -> None:
    err = AppError("oops", trace_id="fixed-trace")
    resp = err.to_response()
    assert isinstance(resp, ErrorResponse)
    assert resp.trace_id == "fixed-trace"
    assert resp.status_code == 500


def test_not_found_error() -> None:
    err = NotFoundError("Project", "proj-1")
    assert err.status_code == 404
    assert err.error == "not_found"
    assert "Project" in err.message
    assert "proj-1" in err.message


def test_not_found_error_no_id() -> None:
    err = NotFoundError("Document")
    assert "Document" in err.message


def test_conflict_error() -> None:
    err = ConflictError("Already exists")
    assert err.status_code == 409
    assert err.error == "conflict"


def test_validation_error() -> None:
    err = ValidationError("Name is required")
    assert err.status_code == 422
    assert err.error == "validation_error"


def test_authentication_error() -> None:
    err = AuthenticationError("Bad credentials")
    assert err.status_code == 401
    assert err.error == "unauthorized"


def test_forbidden_error() -> None:
    err = ForbiddenError("Access denied")
    assert err.status_code == 403
    assert err.error == "forbidden"


def test_rate_limit_error() -> None:
    err = RateLimitError()
    assert err.status_code == 429
    assert err.error == "rate_limit_exceeded"
    assert "Rate limit" in err.message


def test_service_unavailable_error() -> None:
    err = ServiceUnavailableError("Down for maintenance")
    assert err.status_code == 503
    assert err.error == "service_unavailable"


def test_app_error_to_http_exception() -> None:
    from fastapi import HTTPException

    err = NotFoundError("Widget", 42)
    http_exc = err.to_http_exception()
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == 404
    assert http_exc.detail["error"] == "not_found"


# ---------------------------------------------------------------------------
# _default_code helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,expected",
    [
        (400, "bad_request"),
        (401, "unauthorized"),
        (403, "forbidden"),
        (404, "not_found"),
        (409, "conflict"),
        (422, "validation_error"),
        (429, "rate_limit_exceeded"),
        (500, "internal_error"),
        (503, "service_unavailable"),
        (418, "error"),  # unknown code falls back to "error"
    ],
)
def test_default_code(code: int, expected: str) -> None:
    assert _default_code(code) == expected


# ---------------------------------------------------------------------------
# raise_http helper
# ---------------------------------------------------------------------------


def test_raise_http_raises_http_exception() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        raise_http(404, "Not here", code="not_found")
    exc = exc_info.value
    assert exc.status_code == 404
    assert exc.detail["error"] == "not_found"
    assert exc.detail["message"] == "Not here"
    assert exc.detail["trace_id"]


def test_raise_http_custom_trace_id() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        raise_http(400, "Bad input", trace_id="my-trace")
    assert exc_info.value.detail["trace_id"] == "my-trace"


def test_raise_http_with_details() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        raise_http(422, "Validation failed", details={"field": "email"})
    assert exc_info.value.detail["details"] == {"field": "email"}


# ---------------------------------------------------------------------------
# Global exception handlers via the real FastAPI app
# ---------------------------------------------------------------------------


def test_app_error_handler_returns_error_envelope() -> None:
    """AppErrors raised inside route handlers should produce ErrorResponse JSON."""
    from docreview360.errors import NotFoundError
    from fastapi import FastAPI

    mini = FastAPI()

    @mini.get("/boom")
    async def _boom() -> dict:
        raise NotFoundError("Widget", "w1")

    # Register same handlers as the main app
    from docreview360.errors import AppError, error_json_response

    @mini.exception_handler(AppError)
    async def _h(req, exc):  # type: ignore[override]
        return error_json_response(exc)

    client = TestClient(mini, raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "not_found"
    assert "Widget" in body["message"]
    assert body["trace_id"]


def test_main_app_http_exception_uses_envelope() -> None:
    """The main app's HTTPException handler wraps strings in ErrorResponse."""
    from docreview360.api import app

    client = TestClient(app, raise_server_exceptions=False)
    # Hit a route that raises 404 via HTTPException
    resp = client.get("/nonexistent-route-xyz")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert "trace_id" in body
