# SPDX-License-Identifier: MIT
"""Search data models — ProjectModel, SavedSearch."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, model_validator


@dataclass
class SavedSearch:
    """Representation of a saved search query."""

    id: str
    query: str
    user: str
    created: datetime = field(default_factory=lambda: datetime.now(UTC))
    count: int = 0
    flagged_for_review: bool = False


DEFAULT_PROJECT_ID = "demo-project"


class ProjectModel(BaseModel):
    """Representation of a project with assignment metadata."""

    id: str
    name: str
    number: int | None = None
    document_number: str | None = None  # User-provided document number/reference
    user: Optional[str] = None
    # Organization identifier for multi-tenant isolation.
    org_id: int | None = None
    doc_type: str | None = None
    workflow: str | None = None
    requested_workflow: str | None = None
    priority: int = 0
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    temp_user: Optional[str] = None
    temp_until: datetime | None = None
    updated: datetime | None = None  # Add updated field for frontend compatibility
    description: str | None = None
    reviewers: List[str] = Field(default_factory=list)
    # Store the initially requested phase even when no workflow is associated.
    initial_phase: str | None = None

    @computed_field
    def created_at(self) -> datetime:
        """Expose ``created`` under a ``created_at`` alias for API consistency."""
        return self.created

    @computed_field
    def phase(self) -> str | None:
        """Return the current workflow phase, if any."""
        if self.workflow:
            from ..workflows import get_workflow

            wf = get_workflow(self.workflow)
            if wf:
                return wf.phase
        return self.initial_phase

    @computed_field
    def current_phase_id(self) -> str | None:
        """Expose the raw phase identifier for API consumers."""
        if self.workflow:
            from ..workflows import get_workflow

            wf = get_workflow(self.workflow)
            if wf:
                return wf.phase
        return self.initial_phase

    @computed_field
    def status(self) -> str:
        """Derive status from workflow phase or return default."""
        if self.workflow:
            from ..workflows import get_workflow

            wf = get_workflow(self.workflow)
            if wf:
                phase = wf.phase.lower()
                if "draft" in phase or "initial" in phase:
                    return "Draft"
                elif "review" in phase:
                    return "In Progress"
                elif "public comment" in phase:
                    return "In Progress"
                elif "approval" in phase or "final" in phase:
                    return "Complete"
                elif "overdue" in phase:
                    return "Overdue"
                else:
                    return wf.phase
        return "Draft"

    @computed_field
    def title(self) -> str:
        """Alias for name field for frontend compatibility."""
        return self.name

    @computed_field
    def type(self) -> str:
        """Alias for doc_type field for frontend compatibility."""
        return self.doc_type or "Unknown"

    @computed_field
    def progress(self) -> int:
        """Calculate progress based on workflow status."""
        if self.workflow:
            from ..workflows import get_workflow

            wf = get_workflow(self.workflow)
            if wf:
                phase = wf.phase.lower()
                if "draft" in phase or "initial" in phase:
                    return 10
                elif "review" in phase:
                    return 50
                elif "public comment" in phase:
                    return 75
                elif "approval" in phase or "final" in phase:
                    return 90
                else:
                    return 25
        return 0

    @model_validator(mode="after")
    def _ensure_requested_workflow(self) -> "ProjectModel":
        if self.requested_workflow is None and self.workflow:
            self.requested_workflow = self.workflow
        return self
