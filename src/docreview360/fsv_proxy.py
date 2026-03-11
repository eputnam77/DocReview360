# SPDX-License-Identifier: MIT
"""Proxy client for the Federal Style Validator (FSV) service.

When ``FEDERAL_STYLE_VALIDATOR_URL`` is configured, DocReview360 forwards
style/quality/regulatory requests to a running FSV instance instead of
executing the built-in internal implementations.

Usage pattern in endpoint handlers::

    from .fsv_proxy import is_fsv_configured, fsv_validate

    if is_fsv_configured():
        result = await fsv_validate(text, doc_type=doc_type)
    else:
        # fall through to internal implementation
        ...

All proxy functions raise :class:`httpx.HTTPError` (a subclass of
:class:`Exception`) when the upstream FSV service returns an error response.
They raise :class:`NotImplementedError` when FSV is not configured.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

__all__ = [
    "is_fsv_configured",
    "get_fsv_url",
    "fsv_validate",
    "fsv_quality",
    "fsv_regulatory_check",
]

# Default connection timeout (seconds) for FSV proxy calls.
_FSV_TIMEOUT = float(os.getenv("FSV_PROXY_TIMEOUT", "10"))


def get_fsv_url() -> str | None:
    """Return the configured FSV base URL, or ``None`` if not set.

    Reads ``FEDERAL_STYLE_VALIDATOR_URL`` directly from the environment so
    that it works both when a :class:`~docreview360.config.Config` object is
    available and in lightweight contexts such as tests that set the env var
    without loading the full config stack.
    """
    return os.environ.get("FEDERAL_STYLE_VALIDATOR_URL") or None


def is_fsv_configured() -> bool:
    """Return ``True`` when ``FEDERAL_STYLE_VALIDATOR_URL`` is set and non-empty."""
    return bool(get_fsv_url())


async def fsv_validate(text: str, doc_type: str | None = None) -> dict[str, Any]:
    """Proxy a validation request to FSV's ``/validate`` endpoint.

    Args:
        text: The document text (plain-text or HTML) to validate.
        doc_type: Optional document type hint forwarded to FSV.

    Returns:
        The JSON response body from FSV as a plain ``dict``.

    Raises:
        NotImplementedError: When FSV is not configured.
        httpx.HTTPError: When the FSV service returns an error response.
        httpx.TimeoutException: When the FSV service does not respond in time.
    """
    base_url = get_fsv_url()
    if not base_url:
        raise NotImplementedError("FEDERAL_STYLE_VALIDATOR_URL is not configured")
    payload: dict[str, Any] = {"text": text}
    if doc_type is not None:
        payload["doc_type"] = doc_type
    async with httpx.AsyncClient(timeout=_FSV_TIMEOUT) as client:
        response = await client.post(f"{base_url.rstrip('/')}/validate", json=payload)
        response.raise_for_status()
        return response.json()


async def fsv_quality(text: str, document_id: str | None = None) -> dict[str, Any]:
    """Proxy a quality scoring request to FSV's ``/quality`` endpoint.

    Args:
        text: The document text to score.
        document_id: Optional document ID forwarded to FSV for context.

    Returns:
        The JSON response body from FSV as a plain ``dict``.

    Raises:
        NotImplementedError: When FSV is not configured.
        httpx.HTTPError: When the FSV service returns an error response.
        httpx.TimeoutException: When the FSV service does not respond in time.
    """
    base_url = get_fsv_url()
    if not base_url:
        raise NotImplementedError("FEDERAL_STYLE_VALIDATOR_URL is not configured")
    payload: dict[str, Any] = {"text": text}
    if document_id is not None:
        payload["document_id"] = document_id
    async with httpx.AsyncClient(timeout=_FSV_TIMEOUT) as client:
        response = await client.post(f"{base_url.rstrip('/')}/quality", json=payload)
        response.raise_for_status()
        return response.json()


async def fsv_regulatory_check(
    text: str,
    standards: list[str] | None = None,
) -> dict[str, Any]:
    """Proxy a regulatory compliance check to FSV's ``/regulatory-check`` endpoint.

    Args:
        text: The document text to check.
        standards: Optional list of regulatory standard identifiers (e.g.
            ``["21 CFR", "ISO 13485"]``) to limit the check scope.

    Returns:
        The JSON response body from FSV as a plain ``dict``.

    Raises:
        NotImplementedError: When FSV is not configured.
        httpx.HTTPError: When the FSV service returns an error response.
        httpx.TimeoutException: When the FSV service does not respond in time.
    """
    base_url = get_fsv_url()
    if not base_url:
        raise NotImplementedError("FEDERAL_STYLE_VALIDATOR_URL is not configured")
    payload: dict[str, Any] = {"text": text}
    if standards is not None:
        payload["standards"] = standards
    async with httpx.AsyncClient(timeout=_FSV_TIMEOUT) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/regulatory-check", json=payload
        )
        response.raise_for_status()
        return response.json()
