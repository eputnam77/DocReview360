"""SQLAlchemy models for DocReview360."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, text as _sa_text
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


class WebhookSubscriptionRecord(Base):
    """Persistent storage for webhook subscriptions."""

    __tablename__ = "webhook_subscription_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String)
    event: Mapped[str] = mapped_column(String, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(20), index=True)


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
