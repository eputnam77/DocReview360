"""Helpers for synchronising metadata with Metabase."""

from __future__ import annotations

import httpx


def run_field_sync(base_url: str, token: str) -> None:
    """Trigger the Metabase field sync API.

    Parameters
    ----------
    base_url:
        Base URL of the Metabase instance.
    token:
        Session or API token with admin privileges.

    Raises
    ------
    RuntimeError
        If the HTTP request fails.
    """
    url = f"{base_url.rstrip('/')}/api/field/sync"
    try:
        resp = httpx.post(url, headers={"X-Metabase-Session": token}, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network
        raise RuntimeError("Metabase sync failed") from exc
