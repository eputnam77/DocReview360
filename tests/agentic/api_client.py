from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response

from docreview360 import auth

from .models import Actor, ApiTrace, ScenarioState


class AgentApiError(AssertionError):
    """Raised when an API call returns an unexpected status."""


class ActorSession:
    """Small API driver for one seeded actor."""

    def __init__(self, *, actor: Actor, client: TestClient, state: ScenarioState) -> None:
        self.actor = actor
        self.client = client
        self.state = state

    @property
    def headers(self) -> dict[str, str]:
        token = auth.create_access_token({"sub": self.actor.username}, timedelta(minutes=30))
        return {
            "Authorization": f"Bearer {token}",
            "X-User": self.actor.username,
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int | Iterable[int] = 200,
        json: dict[str, Any] | list[Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        expected_statuses = _normalize_expected(expected)
        merged_headers = {**self.headers, **(headers or {})}
        response = self.client.request(
            method,
            path,
            json=json,
            data=data,
            files=files,
            params=params,
            headers=merged_headers,
        )
        trace = ApiTrace(
            actor=self.actor.username,
            method=method,
            path=path,
            expected_statuses=expected_statuses,
            actual_status=response.status_code,
            request_json=json,
            response_json=_safe_response_json(response),
        )
        self.state.traces.append(trace)
        if not trace.ok:
            raise AgentApiError(
                f"{self.actor.username} expected {expected_statuses} from "
                f"{method} {path}, got {response.status_code}: {response.text}"
            )
        return response


def _normalize_expected(expected: int | Iterable[int]) -> tuple[int, ...]:
    if isinstance(expected, int):
        return (expected,)
    statuses = tuple(expected)
    if not statuses:
        raise ValueError("expected statuses must not be empty")
    return statuses


def _safe_response_json(response: Response) -> Any | None:
    try:
        return response.json()
    except ValueError:
        return None
