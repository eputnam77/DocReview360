# SPDX-License-Identifier: MIT
"""Unit tests for src/docreview360/retry.py (R-11)."""

from __future__ import annotations

import pytest


def test_retry_config_defaults() -> None:
    from docreview360.retry import RetryConfig

    cfg = RetryConfig()
    assert cfg.attempts == 3
    assert cfg.backoff == 0.1
    assert cfg.on_retry is None


def test_retry_config_validation_attempts_not_int() -> None:
    from docreview360.retry import RetryConfig

    with pytest.raises(TypeError, match="integer"):
        RetryConfig(attempts=2.5)  # type: ignore[arg-type]


def test_retry_config_validation_attempts_zero() -> None:
    from docreview360.retry import RetryConfig

    with pytest.raises(ValueError, match=">="):
        RetryConfig(attempts=0)


def test_retry_config_validation_backoff_not_number() -> None:
    from docreview360.retry import RetryConfig

    with pytest.raises(TypeError, match="number"):
        RetryConfig(backoff="fast")  # type: ignore[arg-type]


def test_retry_config_validation_backoff_negative() -> None:
    from docreview360.retry import RetryConfig

    with pytest.raises(ValueError, match=">="):
        RetryConfig(backoff=-1.0)


def test_retry_call_success_first_attempt() -> None:
    from docreview360.retry import RetryConfig, retry_call

    calls = []

    def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    result = retry_call(fn, RetryConfig(attempts=3, backoff=0), 7)
    assert result == 14
    assert len(calls) == 1


def test_retry_call_succeeds_on_second_attempt() -> None:
    from docreview360.retry import RetryConfig, retry_call

    call_count = 0

    def flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("not yet")
        return "ok"

    result = retry_call(flaky, RetryConfig(attempts=3, backoff=0))
    assert result == "ok"
    assert call_count == 2


def test_retry_call_exhausts_all_attempts() -> None:
    from docreview360.retry import RetryConfig, retry_call

    call_count = 0

    def always_fails() -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        retry_call(always_fails, RetryConfig(attempts=3, backoff=0))

    assert call_count == 3


def test_retry_call_on_retry_callback_invoked() -> None:
    from docreview360.retry import RetryConfig, retry_call

    retries: list[tuple[int, Exception]] = []

    def on_retry(attempt: int, exc: Exception) -> None:
        retries.append((attempt, exc))

    def always_fails() -> None:
        raise ValueError("x")

    with pytest.raises(ValueError):
        retry_call(always_fails, RetryConfig(attempts=3, backoff=0, on_retry=on_retry))

    # on_retry is called for every failed attempt (all 3)
    assert len(retries) == 3
    assert retries[0][0] == 1
    assert retries[1][0] == 2
    assert retries[2][0] == 3


def test_retry_call_only_catches_specified_exceptions() -> None:
    from docreview360.retry import RetryConfig, retry_call

    call_count = 0

    def raises_type_error() -> None:
        nonlocal call_count
        call_count += 1
        raise TypeError("wrong type")

    # Only catch ValueError; TypeError should propagate immediately
    with pytest.raises(TypeError, match="wrong type"):
        retry_call(
            raises_type_error,
            RetryConfig(attempts=5, backoff=0, exceptions=(ValueError,)),
        )

    assert call_count == 1  # no retries because TypeError is not in exceptions


def test_retry_call_with_kwargs() -> None:
    from docreview360.retry import RetryConfig, retry_call

    def add(a: int, b: int = 0) -> int:
        return a + b

    result = retry_call(add, RetryConfig(attempts=1, backoff=0), 3, b=4)
    assert result == 7
