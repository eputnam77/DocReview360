# SPDX-License-Identifier: MIT
"""Audit models: AuditLog, LogEntry (Pydantic), AuditLogRecord alias."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from ._base import Base, BaseModel

try:  # pragma: no cover - pydantic optional
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(default=None, *, default_factory=None, **kwargs):  # type: ignore[misc]
        """Minimal Field shim when Pydantic is unavailable."""
        if default_factory is not None:
            return default_factory()
        return default


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
