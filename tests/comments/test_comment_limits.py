"""Behavioural tests for comment limits and rate enforcement."""

from datetime import datetime, timedelta, timezone

import pytest
from docreview360 import comments


class TimeStub:
    """Callable helper that returns controllable timestamps."""

    def __init__(self, start: datetime):
        self.current = start

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)

    def __call__(self) -> datetime:
        return self.current


@pytest.fixture(autouse=True)
def reset_state() -> None:
    """Ensure each test starts with a clean comment state."""

    comments.reset_comment_state()
    comments.set_time_provider(None)


def test_comment_max_length_enforced() -> None:
    comments.configure_comment_limits(max_length=10)

    comments.add_comment("doc", "alice", "short")

    with pytest.raises(ValueError, match="maximum length"):
        comments.add_comment("doc", "alice", "toolongtext")


def test_comment_rate_limit_per_user() -> None:
    comments.configure_comment_limits(rate_limit=(2, 60))
    time_stub = TimeStub(datetime(2024, 1, 1, tzinfo=timezone.utc))
    comments.set_time_provider(time_stub)

    comments.add_comment("doc", "alice", "first")
    time_stub.advance(1)
    comments.add_comment("doc", "alice", "second")

    time_stub.advance(1)
    with pytest.raises(ValueError, match="rate limit"):
        comments.add_comment("doc", "alice", "third")

    time_stub.advance(60)
    comments.add_comment("doc", "alice", "after window")


def test_raw_text_retained_and_responses_sanitised() -> None:
    comments.configure_comment_limits(max_length=None, rate_limit=None)
    comment = comments.add_comment(
        "doc",
        "bob",
        "<em>Hello</em> @team",
    )

    rendered = comments.render_comment_for_response(comment)

    assert comment.raw_text == "<em>Hello</em> @team"
    assert rendered.text == "&lt;em&gt;Hello&lt;/em&gt; @team"
    assert rendered.raw_text == "<em>Hello</em> @team"
