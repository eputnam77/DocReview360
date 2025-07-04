"""Lightweight caching layer with optional Redis backend."""

from __future__ import annotations

import os
from typing import Any, Dict

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - fallback when redis not installed
    redis = None

_cache: Dict[str, Any] = {}
_client = None


def _get_client():
    global _client
    if _client is None and redis is not None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            _client = redis.Redis.from_url(url)
            _client.ping()
        except Exception:  # pragma: no cover - redis unreachable
            _client = None
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
