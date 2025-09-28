"""Simple in-memory comment system for collaborative editing."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape, unescape
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CommentModel(BaseModel):
    """Representation of a comment on a document."""

    id: str
    document: str
    user: str
    text: str
    mentions: list[str] = Field(default_factory=list)
    parent: Optional[str] = None
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_comments: Dict[str, List[CommentModel]] = {}
_emoji = {"smile": "😄", "thumbsup": "👍", "rocket": "🚀"}

# Document the small amount of formatting that survives sanitisation.  Mentions and
# emoji short codes remain functional while everything else is escaped to render as
# plain text in HTML clients.
COMMENT_ALLOWED_FORMATTING = (
    "Plain text only. The platform preserves newline characters, ``@mentions`` and "
    "emoji short codes such as ``:rocket:`` while escaping any HTML or Markdown"
    " markup."
)


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

    safe_text = _sanitize_comment_text(unescape(comment.text))
    return comment.model_copy(update={"text": safe_text})


def add_comment(document: str, user: str, text: str, parent: str | None = None) -> CommentModel:
    """Store a comment for the given document parsing mentions and emoji."""
    if not document or not user or not text or not text.strip():
        # ``text`` previously allowed strings containing only whitespace which
        # produced empty, unusable comments.  Reject such input so callers must
        # provide meaningful content.
        raise ValueError("document, user and text are required")
    sanitized_text = _sanitize_comment_text(text.strip())
    mentions = _extract_mentions(sanitized_text)
    comment = CommentModel(
        id=uuid4().hex,
        document=document,
        user=user,
        text=sanitized_text,
        mentions=mentions,
        parent=parent,
    )
    _comments.setdefault(document, []).append(comment)
    return comment


def list_comments(document: str) -> List[CommentModel]:
    """Return comments for a document."""
    return list(_comments.get(document, []))
