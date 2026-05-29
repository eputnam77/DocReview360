# SPDX-License-Identifier: MIT
"""The quality scorer must surface ONNX-critic failures, not swallow them.

quality_assessment() degrades to a heuristic scorer when the ONNX critic cannot
be loaded.  Historically that happened inside a bare ``except Exception`` with no
logging, so a broken or missing model produced silent wrong-looking scores.  The
fallback runs on every call, so the warning must fire exactly once per process
(observable, but not log spam).
"""

from __future__ import annotations

import logging

import pytest

import docreview360.quality as quality


@pytest.fixture(autouse=True)
def _reset_warned() -> None:
    quality._FALLBACK_WARNED = False
    yield
    quality._FALLBACK_WARNED = False


def test_fallback_logs_once_then_stays_quiet(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def _boom(_path: object) -> object:
        raise RuntimeError("model file is a placeholder")

    monkeypatch.setattr(quality, "get_session", _boom)

    with caplog.at_level(logging.WARNING, logger=quality.__name__):
        first = quality.quality_assessment("Some document body text.")
        second = quality.quality_assessment("Another document body text.")

    # The scorer still returns a usable assessment via the heuristic fallback.
    assert 0.0 <= first.score <= 1.0
    assert 0.0 <= second.score <= 1.0

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, "fallback must warn exactly once per process"
    assert "heuristic fallback" in warnings[0].getMessage()
    assert "RuntimeError" in warnings[0].getMessage()
