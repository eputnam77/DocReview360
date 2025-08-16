"""SQLAlchemy models for DocReview360."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
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
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)


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

    project: Mapped[Project] = relationship()
    approvals: Mapped[list["Approval"]] = relationship(back_populates="workflow")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    state: Mapped[str] = mapped_column(String(20), index=True)

    workflow: Mapped[Workflow] = relationship(back_populates="approvals")


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
