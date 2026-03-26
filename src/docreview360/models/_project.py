# SPDX-License-Identifier: MIT
"""Project and document models: Project, Document, DocumentVersion, DocumentQualityScore."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._base import Base
from ._core import DocumentType


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
    # Quality score persistence (Item 35)
    last_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_quality_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plain_language_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)

    project: Mapped[Project] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document")
    branches: Mapped[list["DocumentBranch"]] = relationship(  # type: ignore[name-defined]
        back_populates="document", cascade="all, delete-orphan"
    )
    quality_scores: Mapped[list["DocumentQualityScore"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    content: Mapped[str] = mapped_column(String)

    document: Mapped[Document] = relationship(back_populates="versions")


class DocumentQualityScore(Base):
    """Historical record of a single quality-score run for a document (Item 35)."""

    __tablename__ = "document_quality_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"), index=True, nullable=False
    )
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    plain_language_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    flesch_reading_ease: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="quality_scores")


# Forward reference resolution — DocumentBranch is defined in _records.py but referenced
# in Document.branches above. SQLAlchemy resolves string-quoted refs at mapper config time,
# so no explicit import is needed here.
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from ._records import DocumentBranch  # noqa: F401
