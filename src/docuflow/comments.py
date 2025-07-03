"""Simple in-memory comment system for collaborative editing."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel


class CommentModel(BaseModel):
    """Representation of a comment on a document."""

    id: str
    document: str
    user: str
    text: str
    parent: Optional[str] = None
    created: datetime = datetime.utcnow()


_comments: Dict[str, List[CommentModel]] = {}


def add_comment(document: str, user: str, text: str, parent: str | None = None) -> CommentModel:
    """Store a comment for the given document."""
    comment = CommentModel(id=uuid4().hex, document=document, user=user, text=text, parent=parent)
    _comments.setdefault(document, []).append(comment)
    return comment


def list_comments(document: str) -> List[CommentModel]:
    """Return comments for a document."""
    return list(_comments.get(document, []))
