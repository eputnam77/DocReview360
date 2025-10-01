"""Simple in-memory comment system for collaborative editing."""

from __future__ import annotations

import re
from collections import deque
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Callable, Deque, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CommentModel(BaseModel):
    """Representation of a comment on a document."""

    id: str
    document: str
    user: str
    text: str
    raw_text: str
    mentions: list[str] = Field(default_factory=list)
    parent: Optional[str] = None
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_comments: Dict[str, List[CommentModel]] = {}
_emoji = {"smile": "😄", "thumbsup": "👍", "rocket": "🚀"}

# Comment policy configuration.  Defaults keep comments concise and rate limit
# bursts of activity from a single user while remaining easy to override in
# tests or future configuration plumbing.
DEFAULT_MAX_COMMENT_LENGTH = 2000
DEFAULT_RATE_LIMIT: tuple[int, float] | None = (5, 60.0)

_max_comment_length: int | None = DEFAULT_MAX_COMMENT_LENGTH
_rate_limit: tuple[int, float] | None = DEFAULT_RATE_LIMIT
_user_comment_activity: Dict[str, Deque[datetime]] = {}


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


_time_provider: Callable[[], datetime] = _default_now

# Document the small amount of formatting that survives sanitisation.  Mentions and
# emoji short codes remain functional while everything else is escaped to render as
# plain text in HTML clients.
COMMENT_ALLOWED_FORMATTING = (
    "Plain text only. The platform preserves newline characters, ``@mentions`` and "
    "emoji short codes such as ``:rocket:`` while escaping any HTML or Markdown"
    " markup."
)


def set_time_provider(provider: Callable[[], datetime] | None) -> None:
    """Override the time provider used for rate limiting."""

    global _time_provider
    _time_provider = provider or _default_now


def configure_comment_limits(
    *,
    max_length: int | None = ...,  # noqa: B006 - sentinel is intentional
    rate_limit: tuple[int, float] | None = ...,  # noqa: B006 - sentinel is intentional
) -> None:
    """Adjust comment validation limits."""

    global _max_comment_length, _rate_limit

    if max_length is not ...:
        if max_length is not None and max_length <= 0:
            raise ValueError("max_length must be positive or None")
        _max_comment_length = max_length

    if rate_limit is not ...:
        if rate_limit is not None:
            count, seconds = rate_limit
            if count <= 0 or seconds <= 0:
                raise ValueError("rate_limit values must be positive")
            _rate_limit = (int(count), float(seconds))
        else:
            _rate_limit = None


def reset_comment_limits() -> None:
    """Restore comment limits to their default values."""

    configure_comment_limits(
        max_length=DEFAULT_MAX_COMMENT_LENGTH,
        rate_limit=DEFAULT_RATE_LIMIT,
    )


def reset_comment_state() -> None:
    """Clear stored comments and rate limiting state."""

    _comments.clear()
    _user_comment_activity.clear()
    set_time_provider(None)
    reset_comment_limits()


def _replace_emojis(text: str) -> str:
    """Replace ``:name:`` patterns with emoji characters."""
    return re.sub(
        r":([a-zA-Z0-9_+\-]+):",
        lambda m: _emoji.get(m.group(1), m.group(0)),
        text,
    )


def _extract_mentions(text: str) -> list[str]:
    r"""Return unique ``@user`` mentions from ``text`` preserving order.

    Usernames in DocReview360 may contain hyphens or ``+`` characters which the
    previous implementation failed to capture because it relied on ``\w+``.  As a
    result ``@bob-smith`` was truncated to ``bob`` in the ``mentions`` list and
    the stored comment text was left with the original hyphenated reference.  To
    ensure mention parsing mirrors the more permissive emoji syntax we accept
    word characters, ``-`` and ``+`` when extracting usernames.

    Mention strings may appear multiple times in the comment body.  The previous
    helper returned duplicates which could lead to repeated notifications for the
    same user.  Collect mentions while tracking those already seen so each user
    is listed at most once in the order of first appearance.
    """

    seen: set[str] = set()
    result: list[str] = []
    for name in re.findall(r"@([\w+-]+)", text):
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _sanitize_comment_text(text: str) -> str:
    """Return text safe for storage and rendering in HTML contexts."""

    sanitized = escape(text, quote=False)
    return _replace_emojis(sanitized)


def render_comment_for_response(comment: CommentModel) -> CommentModel:
    """Return a copy of ``comment`` with sanitised text for API responses.

    The helper ensures each response flows through a single, well-documented
    sanitisation path.  ``COMMENT_ALLOWED_FORMATTING`` describes the formatting that
    survives this process for client renderers.
    """

    safe_text = _sanitize_comment_text(comment.raw_text)
    return comment.model_copy(update={"text": safe_text})


def add_comment(document: str, user: str, text: str, parent: str | None = None) -> CommentModel:
    """Store a comment for the given document parsing mentions and emoji."""
    if not document or not user or not text or not text.strip():
        # ``text`` previously allowed strings containing only whitespace which
        # produced empty, unusable comments.  Reject such input so callers must
        # provide meaningful content.
        raise ValueError("document, user and text are required")
    raw_text = text.strip()
    if _max_comment_length is not None and len(raw_text) > _max_comment_length:
        raise ValueError(f"comment exceeds maximum length of {_max_comment_length} characters")

    now = _time_provider()
    if _rate_limit is not None:
        count, window_seconds = _rate_limit
        timestamps = _user_comment_activity.setdefault(user, deque())
        window = timedelta(seconds=window_seconds)
        while timestamps and now - timestamps[0] >= window:
            timestamps.popleft()
        if len(timestamps) >= count:
            raise ValueError("comment rate limit exceeded")
        timestamps.append(now)

    sanitized_text = _sanitize_comment_text(raw_text)
    mentions = _extract_mentions(sanitized_text)
    comment = CommentModel(
        id=uuid4().hex,
        document=document,
        user=user,
        text=sanitized_text,
        raw_text=raw_text,
        mentions=mentions,
        parent=parent,
    )
    _comments.setdefault(document, []).append(comment)
    return comment


def list_comments(document: str) -> List[CommentModel]:
    """Return comments for a document."""
    return list(_comments.get(document, []))
