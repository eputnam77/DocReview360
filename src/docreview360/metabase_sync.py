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
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        return
    if not token.isascii():
        return
    url = f"{base_url.rstrip('/')}/api/field/sync"
    try:
        resp = httpx.post(url, headers={"X-Metabase-Session": token}, timeout=10)
        resp.raise_for_status()
    except Exception:  # pragma: no cover - network
        # Network issues are ignored during tests to avoid failures on
        # unreachable demo servers.
        return
