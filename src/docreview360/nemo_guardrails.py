"""Minimal NeMo-Guardrails style PII checker and middleware."""

from __future__ import annotations

import json
import re
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


def contains_pii(text: str) -> bool:
    """Return ``True`` if the text appears to contain PII such as SSNs."""

    ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    return bool(ssn_pattern.search(text))


class GuardrailsMiddleware(BaseHTTPMiddleware):
    """Simple middleware that blocks requests containing PII."""

    def __init__(self, app: ASGIApp, checker: Callable[[str], bool]):
        super().__init__(app)
        self.checker = checker

    def _contains_pii(self, data: Any) -> bool:
        if isinstance(data, str):
            return self.checker(data)
        if isinstance(data, dict):
            return any(self._contains_pii(v) for v in data.values())
        if isinstance(data, (list, tuple, set)):
            return any(self._contains_pii(v) for v in data)
        return False

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in {"POST", "PUT"}:
            ctype = request.headers.get("content-type", "")
            if "application/json" in ctype:
                try:
                    body_bytes = await request.body()
                    data = json.loads(body_bytes)
                    if self._contains_pii(data):
                        return Response(
                            "Content failed guardrails validation",
                            status_code=400,
                        )
                except Exception:
                    pass
        return await call_next(request)
