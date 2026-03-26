# SPDX-License-Identifier: MIT
"""Standardized retry utilities with exponential back-off.

Replaces the ad-hoc retry loop inside :class:`~docreview360.event_dispatcher.EventDispatcher`
and provides a reusable helper for other modules (e.g. approvals/signatures.py).

Usage::

    from docreview360.retry import retry_call, RetryConfig

    cfg = RetryConfig(attempts=3, backoff=0.1)
    result = retry_call(my_fn, cfg, arg1, kw=val)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

_logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for :func:`retry_call`.

    Attributes:
        attempts:   Total number of attempts (must be >= 1).
        backoff:    Initial sleep in seconds between attempts (>= 0).
                    Each subsequent sleep doubles (exponential back-off).
        exceptions: Tuple of exception types to catch and retry on.
                    Defaults to ``(Exception,)`` — catch everything.
        on_retry:   Optional callback invoked after each failed attempt with
                    the attempt number (1-based) and the caught exception.
    """

    attempts: int = 3
    backoff: float = 0.1
    exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )
    on_retry: Callable[[int, Exception], None] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.attempts, int):
            raise TypeError("attempts must be an integer")
        if self.attempts < 1:
            raise ValueError("attempts must be >= 1")
        if not isinstance(self.backoff, (int, float)):
            raise TypeError("backoff must be a number")
        if self.backoff < 0:
            raise ValueError("backoff must be >= 0")


def retry_call(fn: Callable[..., T], cfg: RetryConfig, /, *args: Any, **kwargs: Any) -> T:
    """Call *fn* with *args*/*kwargs*, retrying up to ``cfg.attempts`` times.

    On each failed attempt the exception is logged at DEBUG level.  If an
    optional ``cfg.on_retry`` callback is provided it is also invoked.  After
    the final attempt the exception propagates to the caller.

    Args:
        fn:     Callable to invoke.
        cfg:    Retry configuration.
        *args:  Positional arguments forwarded to *fn*.
        **kwargs: Keyword arguments forwarded to *fn*.

    Returns:
        The return value of *fn* on success.

    Raises:
        Exception: The last exception raised by *fn* after all attempts are
                   exhausted.
    """
    delay = float(cfg.backoff)
    last_exc: Exception | None = None

    for attempt in range(1, cfg.attempts + 1):
        try:
            return fn(*args, **kwargs)
        except cfg.exceptions as exc:
            last_exc = exc
            _logger.debug(
                "retry_call: attempt %d/%d for %s failed: %s",
                attempt,
                cfg.attempts,
                getattr(fn, "__qualname__", repr(fn)),
                exc,
            )
            if cfg.on_retry is not None:
                try:
                    cfg.on_retry(attempt, exc)
                except Exception:  # never let callback abort the retry loop
                    pass
            if attempt < cfg.attempts:
                time.sleep(delay)
                delay *= 2

    # last_exc is always set here because attempts >= 1 and the loop ran
    raise last_exc  # type: ignore[misc]
