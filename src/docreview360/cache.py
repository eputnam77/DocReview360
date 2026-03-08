"""Lightweight caching layer with optional Redis backend."""

from __future__ import annotations

import logging
import math
import os
import time
from typing import TYPE_CHECKING, Any, Dict, Tuple, cast

_logger = logging.getLogger(__name__)

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
            redis_cls = getattr(_redis, "Redis", None)
            if redis_cls is None:
                raise AttributeError("redis client not available")
            # Some test environments provide a lightweight Redis stub where the
            # ``Redis`` attribute is a simple callable rather than a class with a
            # ``from_url`` constructor.  The previous implementation always
            # attempted to call ``Redis.from_url`` which raised ``AttributeError``
            # for such stubs and permanently marked the client as unreachable.
            # To make the helper more robust we fall back to invoking ``Redis``
            # directly when ``from_url`` is missing.
            if hasattr(redis_cls, "from_url"):
                client = cast(
                    "Redis",
                    redis_cls.from_url(
                        url,
                        socket_connect_timeout=0.1,
                        socket_timeout=0.1,
                    ),
                )
            else:  # pragma: no cover - exercised in tests
                client = cast("Redis", redis_cls(url))
            client.ping()
            _client = client
        except Exception as _conn_exc:
            _logger.warning("Redis unavailable (%s); falling back to in-memory cache", _conn_exc)
            _client = _UNREACHABLE
    if _client is _UNREACHABLE:
        return None
    return cast("Redis | None", _client)


def cache_set(key: str, value: Any, ttl: int | float | None = None) -> None:
    if ttl is not None:
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
            raise TypeError("ttl must be int or float")
        if isinstance(ttl, float) and not math.isfinite(ttl):
            raise ValueError("ttl must be finite")
        if ttl < 0:
            raise ValueError("ttl must be non-negative")
    # A TTL of ``0`` should behave like ``None`` (no expiration) to mirror
    # common cache semantics such as Redis. Without this normalization the
    # local fallback cache would treat ``0`` as an immediate expiry, causing
    # values to vanish right after insertion.
    ttl_arg = ttl if ttl not in (None, 0) else None
    client = _get_client()
    if client:
        client.set(key, value, ex=ttl_arg)
    else:
        expires = time.monotonic() + ttl_arg if ttl_arg is not None else None
        _cache[key] = (value, expires)


def cache_delete(key: str) -> None:
    client = _get_client()
    if client:
        try:
            client.delete(key)
        except Exception as _del_exc:
            _logger.warning("Redis cache_delete failed for key '%s': %s", key, _del_exc)
    _cache.pop(key, None)


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
        try:
            client.flushdb()
        except Exception as _flush_exc:
            # In tests or degraded environments the Redis instance may be
            # unreachable.  Clearing the local fallback cache should still
            # succeed so callers are not left with stale data.
            _logger.warning("Redis flushdb failed: %s", _flush_exc)
    _cache.clear()
