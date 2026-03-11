# SPDX-License-Identifier: MIT
"""SQLAlchemy models for DocReview360."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text as _sa_text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

try:  # pragma: no cover - pydantic optional
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover

    class BaseModel:  # type: ignore[no-redef]
        """Fallback stub when Pydantic is unavailable."""

        def __init__(self, **data: Any) -> None:  # pragma: no cover - simple shim
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:  # pragma: no cover
            return self.__dict__

        def model_validate(self, obj: Any) -> "BaseModel":  # pragma: no cover - convenience
            return obj

        @classmethod
        def model_validate_json(cls, json_data: str) -> "BaseModel":  # pragma: no cover
            import json

            return cls(**json.loads(json_data))

        @classmethod
        def model_json_schema(cls) -> dict[str, Any]:  # pragma: no cover
            return {}


class Base(DeclarativeBase):
    """Base class for all models."""


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    settings_json: Mapped[str | None] = mapped_column(String, nullable=True, server_default="{}")

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped[Organization | None] = relationship(back_populates="users")


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    template: Mapped[str] = mapped_column(String, server_default="")
    workflow: Mapped[list] = mapped_column(JSON, server_default="[]")
    display_order: Mapped[int] = mapped_column(Integer, server_default=_sa_text("0"))
    default_template_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Phase(Base):
    __tablename__ = "phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    display_order: Mapped[int] = mapped_column(Integer, server_default=_sa_text("0"))

    workflow_links: Mapped[list["PhaseWorkflowLink"]] = relationship(
        back_populates="phase", cascade="all, delete-orphan"
    )


class PhaseWorkflowLink(Base):
    __tablename__ = "phase_workflow_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    phase_id: Mapped[int] = mapped_column(ForeignKey("phases.id"), unique=True)
    workflow_template_id: Mapped[str] = mapped_column(String(200))

    phase: Mapped["Phase"] = relationship(back_populates="workflow_links")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    document_type_id: Mapped[int] = mapped_column(ForeignKey("document_types.id"))

    document_type: Mapped[DocumentType] = relationship()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    document_type_id: Mapped[int] = mapped_column(ForeignKey("document_types.id"), index=True)

    document_type: Mapped[DocumentType] = relationship()
    documents: Mapped[list["Document"]] = relationship(back_populates="project")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    content: Mapped[str] = mapped_column(String)

    project: Mapped[Project] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document")
    branches: Mapped[list["DocumentBranch"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    content: Mapped[str] = mapped_column(String)

    document: Mapped[Document] = relationship(back_populates="versions")


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

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, index=True)
    reviewer: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String(20), index=True)
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


class UserSessionRecord(Base):
    """Tracks active user sessions for concurrent-session limits and idle-timeout enforcement."""

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # session_id (random UUID)
    username: Mapped[str] = mapped_column(String, index=True)
    jti: Mapped[str] = mapped_column(String, unique=True, index=True)  # JWT ID
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # "password" | "oidc" | "mfa" | "api_key"
    auth_method: Mapped[str] = mapped_column(String(20), default="password")


class OIDCStateRecord(Base):
    """Ephemeral record for in-flight OIDC Authorization Code + PKCE flows."""

    __tablename__ = "oidc_states"

    state: Mapped[str] = mapped_column(String, primary_key=True)
    nonce: Mapped[str] = mapped_column(String)
    code_verifier: Mapped[str] = mapped_column(String)
    redirect_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Expires after a short window (e.g. 10 minutes)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


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


class WebhookSubscriptionRecord(Base):
    """Persistent storage for webhook subscriptions."""

    __tablename__ = "webhook_subscription_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String)
    event: Mapped[str] = mapped_column(String, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # HMAC-SHA256 secret for signing outgoing payloads; null = unsigned
    signing_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    # Delivery tracking
    delivery_count: Mapped[int] = mapped_column(Integer, server_default=_sa_text("0"))
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "ok" | "failed"


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(20), index=True)


class APIKey(Base):
    """Database model for API keys."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    prefix: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scopes: Mapped[dict[str, Any]] = mapped_column(JSON, default=list)


class ShareLink(Base):
    """Shareable project/document URL tokens."""

    __tablename__ = "share_links"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(20), index=True)  # "project" | "document"
    resource_id: Mapped[str] = mapped_column(String, index=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_by: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    permission: Mapped[str] = mapped_column(String(20), default="read")  # "read" | "comment"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    """Database model storing audit log entries."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user_id: Mapped[str | None] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String, index=True)
    entity_type: Mapped[str | None] = mapped_column(String, index=True)
    entity_id: Mapped[str | None] = mapped_column(String, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    severity: Mapped[str] = mapped_column(String, default="info", index=True)
    ip_address: Mapped[str | None] = mapped_column(String)
    prev_hash: Mapped[str | None] = mapped_column(String, index=True)
    hash: Mapped[str] = mapped_column(String, index=True)
    document_hash: Mapped[str | None] = mapped_column(String)
    provider_response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class LogEntry(BaseModel):
    """Shared Pydantic schema for audit log entries."""

    id: str
    timestamp: datetime
    user_id: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    severity: Literal["info", "warning", "error"] = "info"
    ip_address: str | None = None
    prev_hash: str | None = None
    hash: str = ""
    document_hash: str | None = None
    provider_response: dict[str, Any] = Field(default_factory=dict)

    # Backwards compatibility aliases
    @property
    def metadata(self) -> dict[str, Any]:  # pragma: no cover - simple accessor
        return self.details

    @property
    def context(self) -> dict[str, Any]:  # pragma: no cover - simple accessor
        return self.details

    @property
    def actor(self) -> str | None:  # pragma: no cover - simple accessor
        return self.user_id


# ``AuditLogRecord`` retained for backward compatibility
AuditLogRecord = LogEntry


# ---------------------------------------------------------------------------
# Document branches (parallel review tracks)
# ---------------------------------------------------------------------------


class DocumentBranch(Base):
    """A named branch of a document for parallel review tracks."""

    __tablename__ = "document_branches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    branch_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    source_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_versions.id"), nullable=True
    )
    merged_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_versions.id"), nullable=True
    )
    merged_by: Mapped[str | None] = mapped_column(String, nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="branches")


# ---------------------------------------------------------------------------
# NARA records management metadata
# ---------------------------------------------------------------------------


class NaraMetadata(Base):
    """NARA records management metadata for a document."""

    __tablename__ = "nara_metadata"
    __table_args__ = (UniqueConstraint("document_id", name="uq_nara_document"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    schedule_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    disposition_authority: Mapped[str | None] = mapped_column(String(200), nullable=True)
    retention_period: Mapped[str | None] = mapped_column(String(200), nullable=True)
    disposition_instruction: Mapped[str | None] = mapped_column(String(200), nullable=True)
    record_series_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    record_creator: Mapped[str | None] = mapped_column(String(200), nullable=True)
    record_status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    vital_record: Mapped[bool] = mapped_column(Boolean, default=False)
    classified: Mapped[bool] = mapped_column(Boolean, default=False)
    classification_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Legal hold
# ---------------------------------------------------------------------------


class LegalHold(Base):
    """A legal hold that prevents document disposal."""

    __tablename__ = "legal_holds"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    hold_name: Mapped[str] = mapped_column(String(300), nullable=False)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    released_by: Mapped[str | None] = mapped_column(String, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list["LegalHoldDocument"]] = relationship(
        back_populates="hold", cascade="all, delete-orphan"
    )


class LegalHoldDocument(Base):
    """Join table: documents under a legal hold."""

    __tablename__ = "legal_hold_documents"
    __table_args__ = (UniqueConstraint("hold_id", "document_id", name="uq_hold_document"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    hold_id: Mapped[str] = mapped_column(ForeignKey("legal_holds.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    added_by: Mapped[str] = mapped_column(String, nullable=False)

    hold: Mapped["LegalHold"] = relationship(back_populates="documents")


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
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text|number|date|boolean|select
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
