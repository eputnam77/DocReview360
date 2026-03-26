# SPDX-License-Identifier: MIT
"""Configuration and miscellaneous models: EmailTemplateRecord, GoldenTemplateRecord, OrgConfig,
ProjectConfig, FeatureFlag, CustomWorkflowTemplate, CustomFieldDefinition, CustomFieldValue,
ReviewAssignment, WOPILockRecord."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._base import Base


class EmailTemplateRecord(Base):
    """Persistent storage for email notification templates."""

    __tablename__ = "email_template_records"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String)
    task: Mapped[str | None] = mapped_column(String, nullable=True)


class GoldenTemplateRecord(Base):
    """Persistent storage for golden document template versions."""

    __tablename__ = "golden_template_records"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


# ---------------------------------------------------------------------------
# Hierarchical configuration (system → org → project)
# ---------------------------------------------------------------------------


class OrgConfig(Base):
    """Organization-level configuration overrides."""

    __tablename__ = "org_configs"
    __table_args__ = (UniqueConstraint("org_id", "config_key", name="uq_org_config_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(String(200), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectConfig(Base):
    """Project-level configuration overrides."""

    __tablename__ = "project_configs"
    __table_args__ = (UniqueConstraint("project_id", "config_key", name="uq_project_config_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(String(200), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------


class FeatureFlag(Base):
    """Per-organization or system-wide feature flags."""

    __tablename__ = "feature_flags"
    __table_args__ = (UniqueConstraint("flag_name", "org_id", name="uq_flag_name_org"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    flag_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=100)
    created_by: Mapped[str] = mapped_column(String, default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Custom workflows (org-defined, no code changes)
# ---------------------------------------------------------------------------


class CustomWorkflowTemplate(Base):
    """Organization-defined custom workflow template."""

    __tablename__ = "custom_workflow_templates"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_custom_wf_org_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    doc_types: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array or null
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------------
# Custom fields (EAV — org-defined, no schema changes)
# ---------------------------------------------------------------------------


class CustomFieldDefinition(Base):
    """Definition of a custom field for documents, projects, or users."""

    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        UniqueConstraint("org_id", "entity_type", "field_name", name="uq_custom_field_def"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # document|project|user
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_label: Mapped[str] = mapped_column(String(200), nullable=False)
    field_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # text|number|date|boolean|select
    options: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array for select
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON-encoded
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    values: Mapped[list["CustomFieldValue"]] = relationship(
        back_populates="field_definition", cascade="all, delete-orphan"
    )


class CustomFieldValue(Base):
    """Actual value of a custom field for a specific entity (EAV)."""

    __tablename__ = "custom_field_values"
    __table_args__ = (UniqueConstraint("field_id", "entity_id", name="uq_field_value"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    field_id: Mapped[str] = mapped_column(
        ForeignKey("custom_field_definitions.id"), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    updated_by: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    field_definition: Mapped["CustomFieldDefinition"] = relationship(back_populates="values")


# ---------------------------------------------------------------------------
# Review assignments (Item 44 — reviewer lifecycle model)
# ---------------------------------------------------------------------------


class ReviewAssignment(Base):
    """Persistent reviewer assignment with full lifecycle tracking."""

    __tablename__ = "review_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # invited | reviewing | feedback_submitted | concurred | non_concurred | signed | declined | replaced
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="invited", index=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signature_id: Mapped[str | None] = mapped_column(String, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # FK to another ReviewAssignment.id when this reviewer was replaced
    replaced_by: Mapped[str | None] = mapped_column(String, nullable=True)
    replacement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# WOPI lock records (Item 41 — M365 co-authoring)
# ---------------------------------------------------------------------------


class WOPILockRecord(Base):
    """Persistent WOPI lock for a file currently open in Office Online."""

    __tablename__ = "wopi_lock_records"

    file_id: Mapped[str] = mapped_column(String, primary_key=True)
    lock_token: Mapped[str] = mapped_column(String, nullable=False)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
