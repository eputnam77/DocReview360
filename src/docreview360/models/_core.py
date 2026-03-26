# SPDX-License-Identifier: MIT
"""Core organizational models: Organization, User, DocumentType, Phase, Template."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import (
    text as _sa_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._base import Base


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
    # Python attribute renamed to `default_workflow_template_id`; DB column kept as
    # `default_template_id` for backward compatibility with existing data.  A future
    # Alembic migration can rename the physical column when ready.
    default_workflow_template_id: Mapped[str | None] = mapped_column(
        String(200), name="default_template_id", nullable=True
    )


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
