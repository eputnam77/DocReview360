"""Lightweight caching layer with optional Redis backend."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any, Dict, Tuple, cast

if TYPE_CHECKING:
    from redis import Redis

try:
    import redis as _redis
except Exception:
    _redis = None

# Local in-memory fallback cache. When Redis is unavailable we store a
# tuple of ``(value, expires_at)`` where ``expires_at`` is a monotonic
# timestamp or ``None`` for items without a TTL.
_cache: Dict[str, Tuple[Any, float | None]] = {}
_UNREACHABLE = object()
_client: "Redis | None | object" = None


def _get_client() -> "Redis | None":
    global _client
    if _client is None and _redis is not None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            client = cast(
                "Redis",
                _redis.Redis.from_url(
                    url,
                    socket_connect_timeout=0.1,
                    socket_timeout=0.1,
                ),
            )
            client.ping()
            _client = client
        except Exception:
            _client = _UNREACHABLE
    if _client is _UNREACHABLE:
        return None
    return cast("Redis | None", _client)


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    if ttl is not None and ttl < 0:
        raise ValueError("ttl must be non-negative")
    # A TTL of ``0`` should behave like ``None`` (no expiration) to mirror
    # common cache semantics such as Redis. Previously the local fallback cache
    # treated ``0`` as an immediate expiry making values vanish right after
    # insertion. Normalize ``0`` to ``None`` for consistent behaviour.
    ttl_arg = ttl if ttl not in (None, 0) else None
    client = _get_client()
    if client:
        client.set(key, value, ex=ttl_arg)
    else:
        expires = time.monotonic() + ttl_arg if ttl_arg is not None else None
        _cache[key] = (value, expires)


def cache_get(key: str) -> Any:
    client = _get_client()
    if client:
        return client.get(key)
    item = _cache.get(key)
    if not item:
        return None
    value, expires = item
    if expires is not None and expires <= time.monotonic():
        _cache.pop(key, None)
        return None
    return value


def clear_cache() -> None:
    client = _get_client()
    if client:
        client.flushdb()
    _cache.clear()
