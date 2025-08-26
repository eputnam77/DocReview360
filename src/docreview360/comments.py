"""Simple in-memory comment system for collaborative editing."""

from __future__ import annotations

import re
from datetime import datetime, timezone
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
    created: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


_comments: Dict[str, List[CommentModel]] = {}
_emoji = {"smile": "😄", "thumbsup": "👍", "rocket": "🚀"}


def _replace_emojis(text: str) -> str:
    """Replace ``:name:`` patterns with emoji characters."""
    return re.sub(
        r":([a-zA-Z0-9_+\-]+):",
        lambda m: _emoji.get(m.group(1), m.group(0)),
        text,
    )


def _extract_mentions(text: str) -> list[str]:
    """Return ``@user`` mentions from ``text``."""
    return re.findall(r"@(\w+)", text)


def add_comment(document: str, user: str, text: str, parent: str | None = None) -> CommentModel:
    """Store a comment for the given document parsing mentions and emoji."""
    if not document or not user or not text:
        raise ValueError("document, user and text are required")
    text = _replace_emojis(text)
    mentions = _extract_mentions(text)
    comment = CommentModel(
        id=uuid4().hex,
        document=document,
        user=user,
        text=text,
        mentions=mentions,
        parent=parent,
    )
    _comments.setdefault(document, []).append(comment)
    return comment


def list_comments(document: str) -> List[CommentModel]:
    """Return comments for a document."""
    return list(_comments.get(document, []))
