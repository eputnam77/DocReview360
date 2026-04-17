# SPDX-License-Identifier: MIT
"""Workflow models for workflows, approvals, and persisted workflow state."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._base import Base
from ._project import Project


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    callback_url: Mapped[str | None] = mapped_column(String(200))

    project: Mapped[Project] = relationship()
    approvals: Mapped[list["Approval"]] = relationship(back_populates="workflow")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    state: Mapped[str] = mapped_column(String(20), index=True)

    workflow: Mapped[Workflow] = relationship(back_populates="approvals")


class ApprovalRecord(Base):
    """Persistent storage for approval instances (replaces in-memory dict)."""

    __tablename__ = "approval_records"
    __table_args__ = (
        Index(
            "uq_approval_records_workflow_phase_order",
            "workflow_id",
            "phase_id",
            "approval_order",
            unique=True,
            sqlite_where=text("approval_order <> 0"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, index=True)
    phase_id: Mapped[str] = mapped_column(String, default="", server_default="")
    reviewer: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String(20), index=True)
    approval_order: Mapped[int] = mapped_column(default=0, server_default="0")
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class WorkflowInstanceRecord(Base):
    """Persistent storage for workflow instances (replaces in-memory dict)."""

    __tablename__ = "workflow_instance_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project: Mapped[str] = mapped_column(String, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class WorkflowTemplateRecord(Base):
    """Persistent storage for workflow template definitions."""

    __tablename__ = "workflow_template_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
