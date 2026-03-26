# SPDX-License-Identifier: MIT
"""Records management models: DocumentBranch, NaraMetadata, LegalHold, LegalHoldDocument."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._base import Base
from ._project import Document


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
