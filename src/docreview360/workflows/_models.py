# SPDX-License-Identifier: MIT
"""Workflow data models — ApprovalStep, WorkflowTemplateStep, WorkflowModel, etc."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ApprovalStep(BaseModel):
    """Represents an approval step in a workflow."""

    role: str
    description: str
    order: int
    required: bool = True


class WorkflowTemplateStep(BaseModel):
    """Represents a configurable template step in the admin workflow builder."""

    role: str
    user: str | None = None
    required: bool = True
    description: str | None = None

    @field_validator("role")
    @classmethod
    def _ensure_role(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Workflow template step role is required")
        return value.strip()


class WorkflowTemplatePayload(BaseModel):
    """Payload for creating or updating workflow templates."""

    name: str
    description: str | None = None
    steps: list[WorkflowTemplateStep]

    @field_validator("name")
    @classmethod
    def _ensure_name(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Workflow template name is required")
        return value.strip()

    @field_validator("steps")
    @classmethod
    def _ensure_steps(cls, value: list[WorkflowTemplateStep]) -> list[WorkflowTemplateStep]:
        if not value:
            raise ValueError("Workflow template must include at least one step")
        return value


class WorkflowTemplateModel(BaseModel):
    """Workflow template stored in the backend."""

    id: str
    name: str
    description: str | None = None
    steps: list[WorkflowTemplateStep] = Field(default_factory=list)
    updated: str | None = None

    @field_validator("steps")
    @classmethod
    def _ensure_steps(cls, value: list[WorkflowTemplateStep]) -> list[WorkflowTemplateStep]:
        if not value:
            raise ValueError("Workflow template must include at least one step")
        return value


class WorkflowModel(BaseModel):
    """Simple workflow representation."""

    id: str
    project: str
    phase: str
    phases: List[str]
    # Several list fields previously used mutable list defaults which were
    # shared across model instances.  This led to workflows unexpectedly
    # inheriting reviewers or approval configuration from prior instances.
    # ``default_factory`` ensures each workflow receives its own list.
    reviewers: List[str] = Field(default_factory=list)
    document: Optional[str] = None
    template: str = "branch-coordination"
    approval_steps: List[ApprovalStep] = Field(default_factory=list)
    # distinct roles participating in approvals
    approval_roles: List[str] = Field(default_factory=list)
    # sequence of roles in the order they must approve
    approval_sequence: List[str] = Field(default_factory=list)
    # how approval steps progress: sequential or parallel
    mode: str = "sequential"
    callback_url: str | None = None
