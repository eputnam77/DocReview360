# SPDX-License-Identifier: MIT
"""Session models: UserSessionRecord, OIDCStateRecord."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from ._base import Base


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
