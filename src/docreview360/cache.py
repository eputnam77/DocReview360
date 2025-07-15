"""Lightweight caching layer with optional Redis backend."""

from __future__ import annotations

import os
from typing import Any, Dict

try:
    import redis as _redis
except Exception:  # pragma: no cover - fallback when redis not installed
    _redis = None  # type: ignore[assignment]

_cache: Dict[str, Any] = {}
_client: Any | None | bool = None


def _get_client() -> Any | None:
    global _client
    if _client is None and _redis is not None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            _client = _redis.Redis.from_url(
                url,
                socket_connect_timeout=0.1,
                socket_timeout=0.1,
            )
            _client.ping()
        except Exception:  # pragma: no cover - redis unreachable
            _client = False
    if _client is False:
        return None
    return _client


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    client = _get_client()
    if client:
        client.set(key, value, ex=ttl)
    else:
        _cache[key] = value


def cache_get(key: str) -> Any:
    client = _get_client()
    if client:
        return client.get(key)
    return _cache.get(key)


def clear_cache() -> None:
    client = _get_client()
    if client:
        client.flushdb()
    _cache.clear()
