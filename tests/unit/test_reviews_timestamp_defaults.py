"""Ensure review timestamps are generated per instance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import docreview360.reviews as reviews
from docreview360.reviews import ReviewModel


def test_review_created_timestamp_uses_fresh_default(monkeypatch) -> None:
    """Each new review should receive an independent ``created`` timestamp."""

    real_datetime = reviews.datetime

    class _StubDateTime:
        _counter = 0

        @classmethod
        def now(cls, tz: object | None = None) -> datetime:
            base = real_datetime(2024, 1, 1, tzinfo=UTC)
            value = base + timedelta(seconds=cls._counter)
            cls._counter += 1
            return value

        def __getattr__(self, name: str):  # pragma: no cover - defensive
            return getattr(real_datetime, name)

    monkeypatch.setattr(reviews, "datetime", _StubDateTime)

    review_one = ReviewModel(id="r1", project_id="p", reviewer="alice")
    review_two = ReviewModel(id="r2", project_id="p", reviewer="alice")

    assert review_one.created != review_two.created
