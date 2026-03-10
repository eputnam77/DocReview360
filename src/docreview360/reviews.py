# SPDX-License-Identifier: MIT
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ReviewModel(BaseModel):
    """Simple in-memory representation of a project review."""

    id: str
    project_id: str
    reviewer: str
    status: str = "pending"
    comment: str = ""
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    phase_id: str | None = Field(default=None, alias="phaseId")
    required: bool = True

    model_config = ConfigDict(populate_by_name=True)


class ReviewCreate(BaseModel):
    comment: str
    status: str = "pending"
    phase_id: str | None = Field(default=None, alias="phaseId")
    required: bool = True

    model_config = ConfigDict(populate_by_name=True)


_reviews: Dict[str, List[ReviewModel]] = {}


def reset_reviews() -> None:
    """Clear all stored reviews."""

    _reviews.clear()


def list_reviews(project_id: str, phase_id: str | None = None) -> List[ReviewModel]:
    """Return reviews for a project, optionally filtered by phase."""

    items = _reviews.get(project_id, [])
    if phase_id:
        return [r for r in items if r.phase_id == phase_id]
    return items


def add_review(review: ReviewModel) -> ReviewModel:
    """Store a review in memory."""

    _reviews.setdefault(review.project_id, []).insert(0, review)
    return review


# Pre-populate a demo review for the demo project
add_review(
    ReviewModel(
        id=str(uuid.uuid4()),
        project_id="demo-project",
        reviewer="Demo Reviewer",
        status="approved",
        comment="Looks good!",
        phase_id="draft",
    )
)
