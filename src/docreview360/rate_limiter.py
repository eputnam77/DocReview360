# SPDX-License-Identifier: MIT
"""Distributed Redis-backed rate limiting with in-memory fallback.

The limiter uses a sliding-window counter per key.  When Redis is available it
stores the window in a sorted set (``ZADD`` / ``ZREMRANGEBYSCORE`` pattern)
for accuracy across multiple processes.  When Redis is unavailable the module
falls back to a thread-safe in-memory counter so the application continues to
serve requests with best-effort rate limiting.

Configuration::

    DOCREVIEW360_RATE_LIMIT_ENABLED=1          # enable limiting (default 1)
    DOCREVIEW360_RATE_LIMIT_DEFAULT=100        # default requests per window
    DOCREVIEW360_RATE_LIMIT_WINDOW=60          # window in seconds (default 60)
    DOCREVIEW360_REDIS_URL=redis://localhost:6379/0

Usage (FastAPI dependency)::

    from docreview360.rate_limiter import rate_limit_dep

    @app.get("/endpoint")
    async def endpoint(request: Request, _: None = Depends(rate_limit_dep())):
        ...
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_LIMIT = int(os.environ.get("DOCREVIEW360_RATE_LIMIT_DEFAULT", "100"))
_DEFAULT_WINDOW = int(os.environ.get("DOCREVIEW360_RATE_LIMIT_WINDOW", "60"))
_ENABLED = os.environ.get("DOCREVIEW360_RATE_LIMIT_ENABLED", "1").lower() not in {"0", "false", "no"}

# ── In-memory fallback state ──────────────────────────────────────────────────

_mem_lock = threading.Lock()
# {key: [(timestamp, count), ...]}
_mem_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)


def _mem_check(key: str, limit: int, window: int) -> bool:
    """Sliding-window check using in-memory state. Returns True when allowed."""
    now = time.monotonic()
    cutoff = now - window
    with _mem_lock:
        entries = [e for e in _mem_windows[key] if e[0] > cutoff]
        total = sum(e[1] for e in entries)
        if total >= limit:
            _mem_windows[key] = entries
            return False
        entries.append((now, 1))
        _mem_windows[key] = entries
        return True


def _mem_reset(key: str) -> None:
    with _mem_lock:
        _mem_windows.pop(key, None)


# ── Redis backend ─────────────────────────────────────────────────────────────

_redis_client: Any = None
_redis_checked = False
_redis_lock = threading.Lock()


def _get_redis() -> Any:
    global _redis_client, _redis_checked
    with _redis_lock:
        if _redis_checked:
            return _redis_client
        _redis_checked = True
        url = os.environ.get("DOCREVIEW360_REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis as _redis

            client = _redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
            client.ping()
            _redis_client = client
            log.info("rate_limiter: Redis connected at %s", url)
        except Exception as exc:
            log.warning("rate_limiter: Redis unavailable (%s); using in-memory fallback", exc)
            _redis_client = None
        return _redis_client


def _redis_check(redis: Any, key: str, limit: int, window: int) -> bool:
    """Sliding-window check using Redis sorted set. Returns True when allowed."""
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - (window * 1000)
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, "-inf", cutoff_ms)
    pipe.zadd(key, {f"{now_ms}-{id(pipe)}": now_ms})
    pipe.zcard(key)
    pipe.expire(key, window + 1)
    results = pipe.execute()
    count: int = results[2]
    return count <= limit


# ── Public API ────────────────────────────────────────────────────────────────


def check_rate_limit(
    key: str,
    limit: int = _DEFAULT_LIMIT,
    window: int = _DEFAULT_WINDOW,
) -> bool:
    """Return True when the request is within the rate limit, False when blocked.

    Tries Redis first; falls back to in-memory counter on connection failure.
    When rate limiting is disabled globally, always returns True.
    """
    if not _ENABLED:
        return True

    redis = _get_redis()
    if redis is not None:
        try:
            return _redis_check(redis, key, limit, window)
        except Exception as exc:
            log.warning("rate_limiter: Redis error (%s); falling back to in-memory", exc)

    return _mem_check(key, limit, window)


def reset_for_testing(key: str | None = None) -> None:
    """Reset rate limit counters. For use in tests only."""
    global _redis_client, _redis_checked
    with _redis_lock:
        _redis_checked = False
        _redis_client = None
    if key is not None:
        _mem_reset(key)
    else:
        with _mem_lock:
            _mem_windows.clear()


def rate_limit_dep(
    limit: int = _DEFAULT_LIMIT,
    window: int = _DEFAULT_WINDOW,
    key_func: Any = None,
) -> Any:
    """Return a FastAPI dependency that enforces rate limiting.

    *key_func* is called with the ``Request`` object and must return a string
    key (e.g. client IP, user ID).  Defaults to client IP.

    Example::

        @app.get("/api/resource")
        async def resource(request: Request, _=Depends(rate_limit_dep(limit=10, window=60))):
            ...
    """
    from fastapi import HTTPException, Request

    def _default_key(req: Request) -> str:
        return req.client.host if req.client else "unknown"

    _kf = key_func or _default_key

    async def _dep(request: Request) -> None:
        key = _kf(request)
        if not check_rate_limit(key, limit, window):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {limit} requests per {window}s.",
                headers={"Retry-After": str(window)},
            )

    return _dep
