"""Admin sub-router: /users/*, /profile, /admin/*, /rbac/*, /config, /branding,
/signature-provider, /environments/*, /plugins/*, /plugin-marketplace*."""
from __future__ import annotations

import csv
import io
import logging
import re
import secrets
import string
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .. import auth, rbac, settings_manager
from ..rbac import require_role, get_roles, has_permission
from ..config import CONFIG_FILE, Config
from ..logs import log_event
from ..plugins import load_plugins
from ..plugins import registry as plugin_registry
from ..profile import (
    get_preferences,
    get_profile_data,
    update_preferences,
    update_profile_data,
)
from ..integrations.signature import get_default_providers
from ..settings_manager import update_setting, update_secret
from ..environment import current_environment, load_envs, switch_environment

_logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helper imports needed for multiple routers
# ---------------------------------------------------------------------------

def _is_admin_user(user: auth.User) -> bool:
    from ..rbac import has_role
    return has_role(user.username, "admin")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ProfilePayload(BaseModel):
    """Input model for updating user profile details and preferences."""

    picture: str | None = None
    displayName: str | None = None
    email: str | None = None
    phone: str | None = None
    shorthand: str | None = None
    jobTitle: str | None = None
    department: str | None = None
    timeZone: str | None = None
    dashboards: list[str] | None = None
    permissions: list[str] | None = None
    notificationEmail: bool | None = None
    notificationSMS: bool | None = None
    twoFA: bool | None = None
    theme: Literal["system", "light", "dark"] | None = None
    reduce_motion: bool | None = None


class UserStatusPayload(BaseModel):
    """Payload for toggling a user's active status."""

    active: bool


class UserCreatePayload(BaseModel):
    """Payload for creating a user."""

    username: str
    roles: list[str] = Field(default_factory=list)
    active: bool = True
    password: str | None = None


class UserUpdatePayload(BaseModel):
    """Payload for updating a user."""

    username: str | None = None
    roles: list[str] | None = None
    active: bool | None = None
    password: str | None = None


class UserSummary(BaseModel):
    """Summary information returned by user endpoints."""

    username: str
    roles: list[str]
    active: bool


class RolePermissionUpdate(BaseModel):
    """Payload for updating role permissions."""

    permissions: list[str] = Field(default_factory=list)


class RolePermissionSummary(BaseModel):
    """Role permission summary with default counts."""

    role: str
    permissions: list[str]
    count: int
    default_permissions: list[str]
    default_count: int
    is_default: bool


class UserImportError(BaseModel):
    """Error detail for a single imported row."""

    row: int | None = None
    username: str | None = None
    error: str


class UserImportResult(BaseModel):
    """Summary of user import results."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[UserImportError] = Field(default_factory=list)


class PluginModule(BaseModel):
    """Input model for registering plugins by module path."""

    module: str


class PluginToggle(BaseModel):
    """Input model for enabling or disabling a plugin."""

    name: str


class MarketplaceInstall(BaseModel):
    name: str


_ALLOWED_BRANDING_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_ALLOWED_BRANDING_DATA_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/svg+xml",
}


def _env_int(name: str, default: int) -> int:
    import os
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


_MAX_BRANDING_LOGO_BYTES = _env_int("DOCREVIEW360_BRANDING_MAX_LOGO_BYTES", 256 * 1024)


def _is_valid_branding_href(value: str) -> bool:
    """Return whether ``value`` is a safe local path or HTTP(S) URL."""
    candidate = value.strip()
    if not candidate:
        return False
    if candidate.startswith("/"):
        return True
    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_branding_logo_url(value: str | None) -> str | None:
    """Validate and normalize an optional branding logo URL or data URL."""
    import base64
    import binascii

    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if len(candidate) > 600_000:
        raise ValueError("branding_logo_url is too large")

    lower_candidate = candidate.lower()
    if lower_candidate.startswith("data:"):
        match = re.match(r"^data:(image/[a-z0-9.+-]+);base64,(.+)$", candidate, re.IGNORECASE)
        if match is None:
            raise ValueError("branding_logo_url data URL must be base64 image data")
        mime = match.group(1).lower()
        if mime not in _ALLOWED_BRANDING_DATA_MIME_TYPES:
            raise ValueError("branding_logo_url data URL image type is not allowed")
        payload = match.group(2)
        try:
            decoded = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("branding_logo_url data URL has invalid base64 payload") from exc
        if len(decoded) > _MAX_BRANDING_LOGO_BYTES:
            raise ValueError(
                f"branding_logo_url exceeds size limit of {_MAX_BRANDING_LOGO_BYTES} bytes"
            )
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("branding_logo_url must use https/http or data URL")
    ext = Path(parsed.path or "").suffix.lower() if False else ""
    from pathlib import Path as _Path
    ext = _Path(parsed.path or "").suffix.lower()
    if ext not in _ALLOWED_BRANDING_LOGO_EXTENSIONS:
        raise ValueError("branding_logo_url must use png, jpg, jpeg, webp, or svg")
    return candidate


class SignatureProviderPayload(BaseModel):
    """Payload for selecting active signature providers."""

    primary: str
    fallback: str | None = None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _normalize_import_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _parse_import_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"1", "true", "yes", "y", "on"}:
            return True
        if cleaned in {"0", "false", "no", "n", "off"}:
            return False
    return None


def _split_import_roles(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[;,|]", str(value))
    roles = [str(item).strip().lower() for item in raw_items if str(item).strip()]
    return roles


def _normalize_role_permission(value: str) -> str | None:
    cleaned = value.strip().lower()
    return cleaned if cleaned else None


def _update_role_permissions(role: str, permissions: list[str]) -> None:
    settings = settings_manager.load_settings(settings_manager.SETTINGS_FILE)
    rbac_cfg = settings.get("rbac")
    if not isinstance(rbac_cfg, dict):
        rbac_cfg = {}
    roles_cfg = rbac_cfg.get("roles")
    if not isinstance(roles_cfg, dict):
        roles_cfg = {}
    normalized = []
    for perm in permissions:
        if not isinstance(perm, str):
            continue
        cleaned = _normalize_role_permission(perm)
        if cleaned:
            normalized.append(cleaned)
    roles_cfg[role] = sorted(set(normalized))
    rbac_cfg["roles"] = roles_cfg
    settings_manager.update_setting("rbac", rbac_cfg, settings_manager.SETTINGS_FILE)
    rbac.reload_role_permissions(force=True)


def _generate_password() -> str:
    policy = auth._password_policy()
    class_sets: dict[str, str] = {
        "lowercase": string.ascii_lowercase,
        "uppercase": string.ascii_uppercase,
        "digits": string.digits,
        "symbols": policy.symbol_characters,
    }
    required: list[str] = []
    for class_name in policy.character_classes:
        chars = class_sets.get(class_name)
        if chars:
            required.append(secrets.choice(chars))
    if not required:
        required.append(secrets.choice(string.ascii_letters + string.digits))
    combined = "".join(class_sets.get(name, "") for name in policy.character_classes)
    if not combined:
        combined = string.ascii_letters + string.digits
    length = max(policy.min_length, len(required))
    extra = [secrets.choice(combined) for _ in range(length - len(required))]
    password_chars = required + extra
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def _user_summary(username: str) -> UserSummary:
    return UserSummary(
        username=username,
        roles=sorted(get_roles(username)),
        active=auth.is_active(username),
    )


# ---------------------------------------------------------------------------
# RBAC endpoints
# ---------------------------------------------------------------------------

@router.put("/rbac/role-permissions/{role}", response_model=RolePermissionSummary)
async def update_role_permissions_endpoint(
    role: str,
    body: RolePermissionUpdate,
    user: auth.User = Depends(require_role("admin")),
) -> RolePermissionSummary:
    """Update permissions for a role and persist overrides."""
    normalized_role = role.strip().lower()
    if not normalized_role:
        raise HTTPException(status_code=400, detail="Role required")
    _update_role_permissions(normalized_role, body.permissions)
    current = rbac.get_role_permissions()
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    perms = sorted(current.get(normalized_role, set()))
    default_perms = sorted(defaults.get(normalized_role, set()))
    return RolePermissionSummary(
        role=normalized_role,
        permissions=perms,
        count=len(perms),
        default_permissions=default_perms,
        default_count=len(default_perms),
        is_default=set(perms) == set(default_perms),
    )


@router.delete("/rbac/role-permissions/{role}", response_model=RolePermissionSummary)
async def reset_role_permissions_endpoint(
    role: str,
    user: auth.User = Depends(require_role("admin")),
) -> RolePermissionSummary:
    """Reset a role back to default permissions."""
    normalized_role = role.strip().lower()
    if not normalized_role:
        raise HTTPException(status_code=400, detail="Role required")
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    default_perms = sorted(defaults.get(normalized_role, set()))
    _update_role_permissions(normalized_role, default_perms)
    current = rbac.get_role_permissions()
    perms = sorted(current.get(normalized_role, set()))
    return RolePermissionSummary(
        role=normalized_role,
        permissions=perms,
        count=len(perms),
        default_permissions=default_perms,
        default_count=len(default_perms),
        is_default=set(perms) == set(default_perms),
    )


@router.get("/rbac/role-permissions", response_model=list[RolePermissionSummary])
async def list_role_permissions_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[RolePermissionSummary]:
    """Return role permissions with default counts for UI display."""
    current = rbac.get_role_permissions()
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    roles = sorted(set(defaults) | set(current))
    summaries: list[RolePermissionSummary] = []
    for role in roles:
        perms = sorted(current.get(role, set()))
        default_perms = sorted(defaults.get(role, set()))
        summaries.append(
            RolePermissionSummary(
                role=role,
                permissions=perms,
                count=len(perms),
                default_permissions=default_perms,
                default_count=len(default_perms),
                is_default=set(perms) == set(default_perms),
            )
        )
    return summaries


@router.get("/rbac/matrix", response_model=dict[str, Any])
async def role_permission_matrix_endpoint(
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return the full role-to-permission matrix for visualization."""
    current = rbac.get_role_permissions()
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    all_roles = sorted(set(defaults) | set(current))
    all_permissions: list[str] = sorted(
        {perm for perms in current.values() for perm in perms}
        | {perm for perms in defaults.values() for perm in perms}
    )
    matrix: dict[str, dict[str, bool]] = {}
    for role in all_roles:
        role_perms = set(current.get(role, set()))
        matrix[role] = {perm: (perm in role_perms) for perm in all_permissions}
    return {
        "roles": all_roles,
        "permissions": all_permissions,
        "matrix": matrix,
        "total_roles": len(all_roles),
        "total_permissions": len(all_permissions),
    }


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserSummary])
async def list_users_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> list[UserSummary]:
    """Return all users with role assignments and active status."""
    repo = auth._get_user_repository()
    return [_user_summary(record.username) for record in repo.list_users()]


@router.post("/users/import", response_model=UserImportResult)
@router.post("/api/users/import", response_model=UserImportResult)
async def import_users_endpoint(
    request: Request,
    file: UploadFile | None = File(default=None),
    user: auth.User = Depends(require_role("admin")),
) -> UserImportResult:
    """Import users from CSV or JSON payload."""
    payload: list[dict[str, Any]] | None = None
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        import json as _json

        raw_body = await request.body()
        try:
            payload = _json.loads(raw_body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if file is None and payload is None:
        raise HTTPException(status_code=400, detail="Provide a CSV file or JSON payload")

    rows: list[dict[str, Any]] = []
    roles_present = False

    if file is not None:
        raw = await file.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise HTTPException(status_code=400, detail="CSV is missing a header row")
        roles_present = any(
            _normalize_import_header(name) in {"roles", "role"}
            for name in reader.fieldnames
            if name
        )
        for row in reader:
            rows.append({
                _normalize_import_header(k): v
                for k, v in row.items()
                if k is not None
            })

    if payload is not None:
        if not isinstance(payload, list):
            raise HTTPException(status_code=400, detail="JSON payload must be a list")
        for item in payload:
            if isinstance(item, dict):
                normalized = {
                    _normalize_import_header(str(k)): v for k, v in item.items()
                }
                if "roles" in normalized or "role" in normalized:
                    roles_present = True
                rows.append(normalized)
            else:
                rows.append({"username": str(item)})

    if not rows:
        return UserImportResult()

    repo = auth._get_user_repository()
    result = UserImportResult()

    for idx, raw in enumerate(rows, start=1):
        try:
            username = str(
                raw.get("username")
                or raw.get("email")
                or raw.get("user")
                or ""
            ).strip()
            if not username:
                result.errors.append(UserImportError(row=idx, error="Missing username"))
                result.skipped += 1
                continue

            roles_value: list[str] | None = None
            if roles_present:
                roles_raw = raw.get("roles", raw.get("role"))
                roles_value = _split_import_roles(roles_raw)
                if roles_value is None:
                    roles_value = []

            active_raw = raw.get("active")
            disabled_raw = raw.get("disabled")
            active_val = _parse_import_bool(active_raw)
            disabled_val = _parse_import_bool(disabled_raw)
            if active_val is None and disabled_val is not None:
                active_val = not disabled_val

            password_raw = raw.get("password")
            password = (
                str(password_raw).strip()
                if isinstance(password_raw, str) and password_raw.strip()
                else None
            )

            existing = repo.get_user(username)
            row_status = "skipped"

            if existing is None:
                active = True if active_val is None else active_val
                repo.create_user(
                    username, password or _generate_password(), active=active
                )
                if roles_value is not None:
                    rbac.set_user_roles(
                        username,
                        roles_value,
                        actor="system",
                        context={"source": "import"},
                    )
                row_status = "created"
            else:
                updated_any = False
                active = existing.active if active_val is None else active_val
                if password:
                    repo.create_user(username, password, active=active)
                    updated_any = True
                elif active_val is not None and active != existing.active:
                    repo.set_active(username, active)
                    updated_any = True
                if roles_value is not None:
                    rbac.set_user_roles(
                        username,
                        roles_value,
                        actor="system",
                        context={"source": "import"},
                    )
                    updated_any = True
                row_status = "updated" if updated_any else "skipped"

            profile_updates: dict[str, Any] = {}
            display_name = raw.get("display_name") or raw.get("displayname")
            if isinstance(display_name, str) and display_name.strip():
                profile_updates["displayName"] = display_name.strip()
            organization = raw.get("organization") or raw.get("org") or raw.get("department")
            if isinstance(organization, str) and organization.strip():
                profile_updates["department"] = organization.strip()
            email = raw.get("email")
            if isinstance(email, str) and email.strip():
                profile_updates["email"] = email.strip()
            if profile_updates:
                update_profile_data(username, profile_updates)
                if existing is not None and row_status == "skipped":
                    row_status = "updated"

            if row_status == "created":
                result.created += 1
            elif row_status == "updated":
                result.updated += 1
            else:
                result.skipped += 1
        except Exception as exc:
            result.errors.append(
                UserImportError(
                    row=idx,
                    username=str(raw.get("username") or raw.get("email") or ""),
                    error=str(exc),
                )
            )

    return result


@router.post("/users", response_model=UserSummary, status_code=201)
async def create_user_endpoint(
    body: UserCreatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> UserSummary:
    """Create a user and assign roles."""
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    repo = auth._get_user_repository()
    if repo.get_user(username):
        raise HTTPException(status_code=409, detail="User already exists")
    password = body.password or _generate_password()
    repo.create_user(username, password, active=body.active)
    if body.roles:
        rbac.set_user_roles(username, body.roles, actor="system", context={"source": "api"})
    return _user_summary(username)


@router.put("/users/{username}", response_model=UserSummary)
async def update_user_endpoint(
    username: str,
    body: UserUpdatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> UserSummary:
    """Update a user's name, roles, active flag, or password."""
    repo = auth._get_user_repository()
    record = repo.get_user(username)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    target_username = body.username.strip() if body.username is not None else username
    if body.username is not None and not target_username:
        raise HTTPException(status_code=400, detail="Username required")
    if target_username != username and repo.get_user(target_username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if target_username != username:
        repo.rename_user(username, target_username)
        roles = get_roles(username)
        rbac.set_user_roles(target_username, roles, actor="system", context={"source": "api"})
        rbac.set_user_roles(username, [], actor="system", context={"source": "api"})
        username = target_username
    if body.password:
        repo.create_user(username, body.password, active=record.active)
    if body.active is not None:
        repo.set_active(username, body.active)
    if body.roles is not None:
        rbac.set_user_roles(username, body.roles, actor="system", context={"source": "api"})
    return _user_summary(username)


@router.delete("/users/{username}", response_model=UserSummary)
async def delete_user_endpoint(
    username: str,
    user: auth.User = Depends(require_role("admin")),
) -> UserSummary:
    """Delete a user and remove role assignments."""
    repo = auth._get_user_repository()
    record = repo.get_user(username)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    summary = _user_summary(username)
    repo.delete_user(username)
    rbac.set_user_roles(username, [], actor="system", context={"source": "api"})
    return summary


@router.get("/profile")
async def get_profile(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return profile information for the current user."""
    preferences = get_preferences(current_user.username)
    profile_data = get_profile_data(current_user.username)
    theme = preferences.get("theme", "system")
    if theme not in {"system", "light", "dark"}:
        theme = "system"
    return {
        "username": current_user.username,
        **profile_data,
        "theme": theme,
        "preferences": preferences,
        "roles": sorted(get_roles(current_user.username)),
    }


@router.put("/profile")
async def update_profile(
    body: ProfilePayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Persist profile preference updates."""
    payload = body.model_dump()
    preference_keys = {"theme", "reduce_motion"}
    prefs = {k: v for k, v in payload.items() if k in preference_keys and v is not None}
    profile_updates = {
        k: v for k, v in payload.items() if k not in preference_keys and v is not None
    }
    updated_profile = (
        update_profile_data(current_user.username, profile_updates)
        if profile_updates
        else get_profile_data(current_user.username)
    )
    updated_prefs = (
        update_preferences(current_user.username, prefs) if prefs else get_preferences(current_user.username)
    )
    theme = updated_prefs.get("theme", "system")
    if theme not in {"system", "light", "dark"}:
        theme = "system"
    return {
        "username": current_user.username,
        **updated_profile,
        "theme": theme,
        "preferences": updated_prefs,
        "roles": sorted(get_roles(current_user.username)),
    }


@router.post("/admin/users/{username}/status")
async def set_user_status(
    username: str,
    body: UserStatusPayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Set the active status for ``username`` (admin only)."""
    if not auth.USER_REPOSITORY.get_user(username):
        raise HTTPException(status_code=404, detail="User not found")
    auth.USER_REPOSITORY.set_active(username, body.active)
    return {"username": username, "active": body.active}


@router.get("/admin/panel")
async def admin_panel(user: auth.User = Depends(require_role("admin"))) -> dict[str, str]:
    """Return a trivial payload for admin-only access."""
    return {"user": user.username, "admin": "ok"}


# ---------------------------------------------------------------------------
# Plugin endpoints
# ---------------------------------------------------------------------------

@router.get("/plugins")
async def list_plugins(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """Return metadata about registered plugins."""
    return plugin_registry.info()


@router.post("/plugins", status_code=201)
async def register_plugin(
    body: PluginModule,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, list[str]]:
    """Load and register plugins from a module path."""
    try:
        load_plugins([body.module])
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"names": plugin_registry.all()}


@router.put("/plugins/{name}/enable")
async def enable_plugin(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Enable a disabled plugin."""
    try:
        plugin_registry.enable(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"enabled": name}


@router.put("/plugins/{name}/disable")
async def disable_plugin(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Disable a plugin."""
    try:
        plugin_registry.disable(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"disabled": name}


@router.delete("/plugins/{name}", status_code=204, response_class=Response)
async def unregister_plugin(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Unregister a plugin entirely."""
    try:
        plugin_registry.unregister(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Plugin marketplace
# ---------------------------------------------------------------------------

@router.get("/plugin-marketplace")
async def list_marketplace(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """Return available plugins with detailed information."""
    from ..plugin_marketplace import list_plugins_with_info
    return list_plugins_with_info()


@router.post("/plugin-marketplace/install")
async def install_marketplace_plugin(
    body: MarketplaceInstall,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Install a plugin from the marketplace."""
    from ..plugin_marketplace import install_plugin
    try:
        install_plugin(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"installed": body.name}


# ---------------------------------------------------------------------------
# Config endpoint
# ---------------------------------------------------------------------------

class ConfigPayload(BaseModel):
    """Configuration parameters for integrations."""

    database: str
    database_url: str | None = None
    editor: str
    cms: str
    auth: str
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    ai_auto_assign_writers: bool = False
    filename_template: str = "{id}"
    inactivity_timeout_minutes: int = Field(default=30, ge=1)
    branding_company_name: str = Field(default="DocReview360", max_length=80)
    branding_logo_url: str | None = None
    branding_logo_alt: str = Field(default="Organization logo", max_length=120)
    branding_support_url: str = Field(default="/docs/", max_length=255)
    branding_docs_url: str = Field(default="/docs/", max_length=255)
    branding_security_url: str = Field(default="/security", max_length=255)
    branding_privacy_url: str = Field(default="/privacy", max_length=255)

    @field_validator("branding_company_name")
    @classmethod
    def _validate_branding_company_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("branding_company_name cannot be empty")
        return normalized

    @field_validator("branding_logo_url")
    @classmethod
    def _validate_branding_logo_url(cls, value: str | None) -> str | None:
        return _normalize_branding_logo_url(value)

    @field_validator(
        "branding_support_url",
        "branding_docs_url",
        "branding_security_url",
        "branding_privacy_url",
    )
    @classmethod
    def _validate_branding_link(cls, value: str) -> str:
        normalized = value.strip()
        if not _is_valid_branding_href(normalized):
            raise ValueError("branding link must be an absolute path or http(s) URL")
        return normalized

    @model_validator(mode="after")
    def _validate_logo_alt(self) -> "ConfigPayload":
        if self.branding_logo_url and not self.branding_logo_alt.strip():
            raise ValueError("branding_logo_alt is required when branding_logo_url is set")
        self.branding_logo_alt = self.branding_logo_alt.strip() or "Organization logo"
        return self


@router.get("/config", response_model=ConfigPayload)
async def get_config_endpoint(user: auth.User = Depends(require_role("admin"))) -> ConfigPayload:
    """Return the current application configuration."""
    cfg = Config.load(CONFIG_FILE)
    if cfg is None:
        cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="oidc")
    return ConfigPayload(**cfg.__dict__)


@router.put("/config", response_model=ConfigPayload)
async def update_config_endpoint(
    payload: ConfigPayload,
    user: auth.User = Depends(require_role("admin")),
) -> ConfigPayload:
    """Persist a new configuration."""
    cfg = Config(**payload.model_dump())
    try:
        cfg.save(CONFIG_FILE)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return payload


# ---------------------------------------------------------------------------
# Signature provider
# ---------------------------------------------------------------------------

@router.get("/signature-provider")
async def get_signature_provider_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str | None]:
    """Return the configured signature providers."""
    providers = get_default_providers()
    primary = providers[0] if providers else None
    fallback = providers[1] if len(providers) > 1 else None
    return {"primary": primary, "fallback": fallback}


@router.put("/signature-provider")
async def update_signature_provider_endpoint(
    payload: SignatureProviderPayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str | None]:
    """Persist the active signature provider selection."""
    update_setting("signature_provider_primary", payload.primary)
    update_setting("signature_provider_fallback", payload.fallback)
    return {"primary": payload.primary, "fallback": payload.fallback}


# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------

@router.get("/environments")
async def list_environments(
    _user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return available environments and the current one (admin only)."""
    return {"current": current_environment(), "envs": load_envs()}


@router.post("/environments/{name}")
async def switch_env_endpoint(
    name: str,
    _user: auth.User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Switch the active environment and return its URL."""
    try:
        url = switch_environment(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"url": url}
