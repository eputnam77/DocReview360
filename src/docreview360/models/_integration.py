# SPDX-License-Identifier: MIT
"""Integration models: WebhookSubscriptionRecord, Plugin, BuiltinPluginStateRecord, OrgToolConfig, APIKey, ShareLink."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    String,
    text as _sa_text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ._base import Base


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


class BuiltinPluginStateRecord(Base):
    """Persistent toggle state for built-in plugins (replaces in-memory dict)."""

    __tablename__ = "builtin_plugin_states"

    plugin_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class OrgToolConfig(Base):
    """Per-organization plugin/tool configuration overrides."""

    __tablename__ = "org_tool_configs"

    org_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    # List of marketplace plugin IDs that are disabled for this org.
    disabled_plugins: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Dict of builtin_id -> bool overrides (applied on top of global state).
    enabled_builtins: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)


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
