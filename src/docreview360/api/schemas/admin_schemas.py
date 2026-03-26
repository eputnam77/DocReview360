# SPDX-License-Identifier: MIT
"""Typed Pydantic response schemas for admin endpoints (R-13).

These replace the raw ``dict`` return types on admin endpoints, giving
consumers a stable, documented contract and enabling OpenAPI schema generation.

Import pattern::

    from .schemas.admin_schemas import UserResponse, RbacMatrixResponse, ...
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    """A single user record returned by the admin user-management endpoints."""

    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool = False
    roles: list[str] = Field(default_factory=list)
    mfa_enabled: bool = False
    locale: str | None = None


class UserListResponse(BaseModel):
    """Response for GET /users."""

    users: list[UserResponse]
    total: int


class UserCreateResponse(BaseModel):
    """Response for POST /users."""

    username: str
    message: str = "User created"


class UserUpdateResponse(BaseModel):
    """Response for PUT /users/{username}."""

    username: str
    updated: list[str] = Field(default_factory=list, description="List of updated field names")
    message: str = "User updated"


class UserDeleteResponse(BaseModel):
    """Response for DELETE /users/{username}."""

    username: str
    deleted: bool = True


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class RolePermissionsResponse(BaseModel):
    """Response for GET /rbac/roles/{role}/permissions."""

    role: str
    permissions: list[str]


class RbacMatrixResponse(BaseModel):
    """Response for GET /rbac/matrix — full role→permissions mapping."""

    matrix: dict[str, list[str]]


class RoleUpdateResponse(BaseModel):
    """Response for PUT /rbac/roles/{role}/permissions."""

    role: str
    permissions: list[str]
    message: str = "Permissions updated"


# ---------------------------------------------------------------------------
# Plugins and marketplace
# ---------------------------------------------------------------------------


class PluginResponse(BaseModel):
    """A single plugin record."""

    name: str
    enabled: bool = False
    version: str | None = None
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class PluginListResponse(BaseModel):
    """Response for GET /plugins."""

    plugins: list[PluginResponse]


class BuiltinPluginStatusResponse(BaseModel):
    """Response for GET /admin/builtin-plugin-status."""

    name: str
    enabled: bool
    available: bool = True


# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------


class BrandingResponse(BaseModel):
    """Response for GET /admin/branding."""

    org_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    favicon_url: str | None = None


# ---------------------------------------------------------------------------
# Signature provider
# ---------------------------------------------------------------------------


class SignatureProviderResponse(BaseModel):
    """Response for GET /admin/signature-provider."""

    provider: str
    configured: bool = False


# ---------------------------------------------------------------------------
# General purpose admin action responses
# ---------------------------------------------------------------------------


class AdminActionResponse(BaseModel):
    """Generic success/failure response for admin write operations."""

    ok: bool = True
    message: str = "Success"
    detail: dict[str, Any] = Field(default_factory=dict)


class OrgToolsResponse(BaseModel):
    """Response for GET /admin/org/tools."""

    tools: dict[str, bool] = Field(default_factory=dict)


class LocaleResponse(BaseModel):
    """A single supported locale entry."""

    code: str
    name: str
    rtl: bool = False


class LocaleListResponse(BaseModel):
    """Response for GET /admin/locales."""

    locales: list[LocaleResponse]


class AutoValidationSettingResponse(BaseModel):
    """Response for GET /admin/auto-validation."""

    enabled: bool
    triggers: list[str] = Field(default_factory=list)


class FsvCheckSettingsResponse(BaseModel):
    """Response for GET /admin/fsv-check-settings."""

    enabled: bool
    checks: list[str] = Field(default_factory=list)
    severity: str = "warning"


class FsvUrlSettingResponse(BaseModel):
    """Response for GET /admin/fsv-url."""

    url: str | None = None
