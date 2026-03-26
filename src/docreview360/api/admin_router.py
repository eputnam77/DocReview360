# SPDX-License-Identifier: MIT
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

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator

from .. import auth, rbac, settings_manager
from ..config import CONFIG_FILE, Config
from ..environment import current_environment, load_envs, switch_environment
from ..integrations.signature import get_default_providers
from ..plugins import load_plugins
from ..plugins import registry as plugin_registry
from ..profile import (
    get_preferences,
    get_profile_data,
    update_preferences,
    update_profile_data,
)
from ..rbac import get_roles, require_role
from ..settings_manager import update_setting
from .admin_rbac_router import router as rbac_router

_logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(rbac_router)


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


# ---------------------------------------------------------------------------
# User locale preference endpoints
# ---------------------------------------------------------------------------


class LocalePayload(BaseModel):
    """Payload for updating the current user's locale preference."""

    locale: str


@router.get("/users/me/locale")
async def get_user_locale(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Return the locale preference for the currently authenticated user."""
    from ..profile import VALID_LOCALES, get_preferences

    prefs = get_preferences(current_user.username)
    locale = prefs.get("locale", "en")
    if locale not in VALID_LOCALES:
        locale = "en"
    return {"locale": locale}


@router.put("/users/me/locale")
async def set_user_locale(
    body: LocalePayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Persist the locale preference for the currently authenticated user."""
    from ..profile import VALID_LOCALES, update_preferences

    normalized = body.locale.strip().lower()
    if normalized not in VALID_LOCALES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported locale {body.locale!r}. Must be one of: {sorted(VALID_LOCALES)}",
        )
    update_preferences(current_user.username, {"locale": normalized})
    return {"locale": normalized}


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


@router.delete("/plugins/{name}", status_code=204, response_class=Response, response_model=None)
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


@router.get("/plugin-marketplace/builtin-status")
async def get_builtin_plugin_status(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, bool]:
    """Return the enabled/disabled state of each built-in plugin."""
    from ..plugin_marketplace import get_builtin_status
    return get_builtin_status()


class MarketplaceToggle(BaseModel):
    """Request body for toggling a built-in plugin."""

    pluginId: str
    enabled: bool


@router.post("/plugin-marketplace/toggle")
async def toggle_builtin_plugin(
    body: MarketplaceToggle,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Enable or disable a built-in plugin."""
    from ..plugin_marketplace import set_builtin_plugin_state
    try:
        set_builtin_plugin_state(body.pluginId, body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"pluginId": body.pluginId, "enabled": body.enabled}


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


@router.get("/admin/audit/completeness")
async def audit_completeness(
    _user: auth.User = Depends(require_role("admin")),
) -> dict:
    """Verify the integrity of the audit log hash chain (admin only).

    Returns ``{"ok": true}`` if the chain is intact, or ``{"ok": false, ...}``
    with the ID of the first broken entry.
    """
    from ..logs import verify_audit_log_chain

    result = verify_audit_log_chain()
    if isinstance(result, dict):
        return result
    # If it returns a simple bool or tuple, normalise
    if result is True:
        return {"ok": True, "message": "Audit log chain is intact"}
    return {"ok": False, "message": "Audit log chain verification failed", "detail": str(result)}


# ---------------------------------------------------------------------------
# Branding / white-label endpoints  (Item 40 Phase 3 / Item 42)
# ---------------------------------------------------------------------------


class BrandingPayload(BaseModel):
    """Partial branding overrides — only provided keys are written."""

    company_name: str | None = None
    logo_url: str | None = None
    logo_alt: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    sidebar_bg: str | None = None
    sidebar_text: str | None = None
    favicon_url: str | None = None
    support_url: str | None = None
    docs_url: str | None = None
    privacy_url: str | None = None
    security_url: str | None = None
    locale: str | None = None


class TerminologyPayload(BaseModel):
    """Partial terminology overrides — only provided keys are written."""

    project: str | None = None
    projects: str | None = None
    document: str | None = None
    documents: str | None = None
    approval: str | None = None
    reviewer: str | None = None


@router.get("/orgs/{org_id}/branding")
async def get_org_branding(
    org_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return effective branding + terminology for *org_id*."""
    from ..branding import get_full_theme
    from ..db_store import get_db

    with get_db().orm_session() as db:
        return get_full_theme(db, org_id)


@router.put("/orgs/{org_id}/branding")
async def set_org_branding(
    org_id: str,
    payload: BrandingPayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Update branding overrides for *org_id* (admin only)."""
    from ..branding import set_branding
    from ..db_store import get_db

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No branding fields provided")
    with get_db().orm_session() as db:
        try:
            result = set_branding(db, org_id, updated_by=current_user.username, **updates)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"org_id": org_id, "branding": result}


@router.delete("/orgs/{org_id}/branding")
async def reset_org_branding(
    org_id: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Reset all branding overrides for *org_id* to system defaults."""
    from ..branding import reset_branding
    from ..db_store import get_db

    with get_db().orm_session() as db:
        result = reset_branding(db, org_id, updated_by=current_user.username)
        return {"org_id": org_id, "branding": result, "reset": True}


@router.put("/orgs/{org_id}/terminology")
async def set_org_terminology(
    org_id: str,
    payload: TerminologyPayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Update terminology overrides for *org_id* (admin only)."""
    from ..branding import set_terminology
    from ..db_store import get_db

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No terminology fields provided")
    with get_db().orm_session() as db:
        try:
            result = set_terminology(db, org_id, updated_by=current_user.username, **updates)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"org_id": org_id, "terminology": result}


# ---------------------------------------------------------------------------
# Per-org tool configuration endpoints
# ---------------------------------------------------------------------------


class OrgToolConfigPayload(BaseModel):
    """Request body for updating per-org tool configuration."""

    disabled_plugins: list[str] | None = None


class OrgBuiltinStatusPayload(BaseModel):
    """Request body for updating per-org builtin plugin overrides."""

    pluginId: str
    enabled: bool


@router.get("/orgs/{org_id}/tools")
async def get_org_tools(
    org_id: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return tool configuration and effective plugin list for *org_id*."""
    from ..plugin_marketplace import get_effective_plugins, get_org_tool_config

    config = get_org_tool_config(org_id)
    plugins = get_effective_plugins(org_id)
    return {
        "org_id": org_id,
        "config": config,
        "plugins": plugins,
    }


@router.put("/orgs/{org_id}/tools")
async def update_org_tools(
    org_id: str,
    payload: OrgToolConfigPayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Update tool configuration overrides for *org_id*."""
    from ..plugin_marketplace import set_org_tool_config

    try:
        config = set_org_tool_config(
            org_id,
            disabled_plugins=payload.disabled_plugins,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"org_id": org_id, "config": config}


@router.get("/orgs/{org_id}/tools/builtin-status")
async def get_org_builtin_status(
    org_id: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return effective builtin plugin status for *org_id* (global + org overrides)."""
    from ..plugin_marketplace import get_builtin_status, get_org_tool_config

    global_status = get_builtin_status(org_id=org_id)
    org_cfg = get_org_tool_config(org_id)
    return {
        "org_id": org_id,
        "status": global_status,
        "org_overrides": org_cfg.get("enabled_builtins", {}),
    }


@router.put("/orgs/{org_id}/tools/builtin-status")
async def set_org_builtin_status(
    org_id: str,
    payload: OrgBuiltinStatusPayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Set a per-org builtin plugin override for *org_id*."""
    from ..plugin_marketplace import BUILTIN_PLUGIN_IDS, get_builtin_status, set_org_tool_config

    if payload.pluginId not in BUILTIN_PLUGIN_IDS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown built-in plugin: {payload.pluginId!r}",
        )
    try:
        # Merge the new override into the existing org config.
        from ..plugin_marketplace import get_org_tool_config
        existing = get_org_tool_config(org_id)
        overrides = dict(existing.get("enabled_builtins", {}))
        overrides[payload.pluginId] = payload.enabled
        config = set_org_tool_config(org_id, enabled_builtins=overrides)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    effective = get_builtin_status(org_id=org_id)
    return {
        "org_id": org_id,
        "pluginId": payload.pluginId,
        "enabled": payload.enabled,
        "effective_status": effective,
        "config": config,
    }


# ---------------------------------------------------------------------------
# i18n / locale endpoints
# ---------------------------------------------------------------------------


@router.get("/i18n/locales")
async def list_supported_locales(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """Return the list of supported UI locales."""
    from ..i18n import list_locales

    return list_locales()


@router.get("/i18n/translations/{locale}")
async def get_translations(
    locale: str,
    namespace: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return translation strings for *locale*, optionally filtered by *namespace*."""
    from ..i18n import SUPPORTED_LOCALES, _normalise, get_namespace

    # Check the raw base tag before normalisation so that unsupported locales
    # (e.g. "zh") are rejected rather than silently mapped to the default.
    raw_base = locale.strip().lower().split("-")[0].split("_")[0]
    if raw_base not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=404, detail=f"Locale {locale!r} is not supported")
    norm = _normalise(locale)

    if namespace:
        strings = get_namespace(namespace, norm)
        return {"locale": norm, "namespace": namespace, "strings": strings}

    # Return all namespaces
    from ..i18n import _TRANSLATIONS

    all_strings = {}
    for key in _TRANSLATIONS:
                from ..i18n import translate
                all_strings[key] = translate(key, norm)
    return {"locale": norm, "strings": all_strings}


def _get_merged_translations(org_id: str, locale: str) -> dict[str, str]:
    """Return all translation strings for *locale* with org terminology overrides applied.

    Terminology overrides replace the corresponding nav/common keys so that e.g.
    setting ``terminology.projects = "Cases"`` causes ``nav.projects`` → ``"Cases"``.

    The mapping from branding terminology keys to translation string keys is:
      - ``project``   → ``nav.project`` (singular, used in breadcrumbs etc.)
      - ``projects``  → ``nav.projects`` (plural nav label)
      - ``document``  → ``nav.document``
      - ``documents`` → ``nav.documents``
      - ``approval``  → ``approval.*`` keys are untouched; label stored in
                        ``approval.label`` if present
      - ``reviewer``  → no direct nav key; stored at ``terminology.reviewer``
    """
    from ..branding import TERMINOLOGY_DEFAULTS, get_terminology
    from ..i18n import _TRANSLATIONS, SUPPORTED_LOCALES, _normalise, translate

    raw_base = locale.strip().lower().split("-")[0].split("_")[0]
    if raw_base not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=404, detail=f"Locale {locale!r} is not supported")
    norm = _normalise(locale)

    # Build base strings
    all_strings: dict[str, str] = {key: translate(key, norm) for key in _TRANSLATIONS}

    # Fetch org terminology overrides
    from ..db_store import get_db

    try:
        with get_db().orm_session() as db:
            terminology = get_terminology(db, org_id)
    except Exception:
        terminology = dict(TERMINOLOGY_DEFAULTS)

    # Apply terminology overrides on top of translations.
    # Each terminology key maps to one or more translation string keys.
    _TERM_TO_TRANSLATION_KEYS: dict[str, list[str]] = {
        "project": ["nav.project"],
        "projects": ["nav.projects"],
        "document": ["nav.document"],
        "documents": ["nav.documents"],
    }
    for term_key, trans_keys in _TERM_TO_TRANSLATION_KEYS.items():
        value = terminology.get(term_key)
        default = TERMINOLOGY_DEFAULTS.get(term_key, "")
        if value and value != default:
            for trans_key in trans_keys:
                all_strings[trans_key] = value

    # Also expose raw terminology values under a ``terminology.*`` namespace
    # so frontends can access them directly.
    for term_key, value in terminology.items():
        all_strings[f"terminology.{term_key}"] = value

    return all_strings


@router.get("/i18n/terminology/{locale}")
async def get_terminology_translations(
    locale: str,
    org_id: str = "default",
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return merged translations for *locale* with org-specific terminology overrides.

    Pass ``?org_id=<org>`` to apply that org's terminology overrides on top of
    the base locale strings.  When the org has e.g. ``terminology.projects = "Cases"``,
    the ``nav.projects`` string is replaced with ``"Cases"`` in the response.

    Without an ``org_id`` (or when the org has no overrides) the response is
    identical to ``GET /i18n/translations/{locale}``.
    """
    try:
        strings = _get_merged_translations(org_id, locale)
    except HTTPException:
        raise
    from ..i18n import SUPPORTED_LOCALES, _normalise

    raw_base = locale.strip().lower().split("-")[0].split("_")[0]
    if raw_base not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=404, detail=f"Locale {locale!r} is not supported")
    norm = _normalise(locale)
    return {"locale": norm, "org_id": org_id, "strings": strings}


# ---------------------------------------------------------------------------
# Item 34 Phase 3 — On-save auto-validation setting
# ---------------------------------------------------------------------------

class _AutoValidationRequest(BaseModel):
    enabled: bool
    """Whether to run document preflight validation automatically after each save."""


@router.get("/admin/settings/auto-validation")
async def get_auto_validation_setting(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, bool]:
    """Return the global on-save auto-validation toggle (admin or authenticated user)."""
    settings = settings_manager.load_settings()
    return {"enabled": bool(settings.get("auto_save_validation", True))}


@router.put("/admin/settings/auto-validation")
async def set_auto_validation_setting(
    body: _AutoValidationRequest,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, bool]:
    """Enable or disable global on-save auto-validation. Requires admin role."""
    settings_manager.update_setting("auto_save_validation", body.enabled)
    return {"enabled": body.enabled}


# ---------------------------------------------------------------------------
# Item 48 — Per-check granularity for FSV rule categories
# ---------------------------------------------------------------------------

#: Canonical list of FSV check category IDs recognised by DocReview360.
FSV_CHECK_CATEGORIES: list[str] = [
    "passive_voice",
    "acronym_validation",
    "heading_structure",
    "readability",
    "regulatory",
    "plain_language",
]

_DEFAULT_FSV_CHECKS: dict[str, bool] = {c: True for c in FSV_CHECK_CATEGORIES}


class _FsvChecksRequest(BaseModel):
    checks: dict[str, bool]
    """Map of check-category ID → enabled. Unknown keys are ignored."""


@router.get("/admin/settings/fsv-checks")
async def get_fsv_check_settings(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, object]:
    """Return per-category FSV check enable/disable state and the canonical category list."""
    settings = settings_manager.load_settings()
    stored: dict[str, bool] = settings.get("fsv_check_categories", {})
    checks = {c: stored.get(c, True) for c in FSV_CHECK_CATEGORIES}
    return {"checks": checks, "categories": FSV_CHECK_CATEGORIES}


@router.put("/admin/settings/fsv-checks")
async def set_fsv_check_settings(
    body: _FsvChecksRequest,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, object]:
    """Enable or disable individual FSV check categories. Requires admin role."""
    settings = settings_manager.load_settings()
    stored: dict[str, bool] = dict(settings.get("fsv_check_categories", {}))
    for key, val in body.checks.items():
        if key in FSV_CHECK_CATEGORIES:
            stored[key] = bool(val)
    settings_manager.update_setting("fsv_check_categories", stored)
    checks = {c: stored.get(c, True) for c in FSV_CHECK_CATEGORIES}
    return {"checks": checks}


# ---------------------------------------------------------------------------
# Item 34 Phase 2 — FSV URL configuration via settings API
# ---------------------------------------------------------------------------


class _FsvUrlRequest(BaseModel):
    url: str | None = None
    """Base URL of the FSV service (e.g. http://localhost:8080). Empty string clears."""


@router.get("/admin/settings/fsv-url")
async def get_fsv_url_setting(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, object]:
    """Return the currently configured FSV base URL (admin or authenticated user)."""
    from ..fsv_proxy import get_fsv_url, is_fsv_configured

    return {
        "url": get_fsv_url(),
        "configured": is_fsv_configured(),
        "source": "env" if __import__("os").environ.get("FEDERAL_STYLE_VALIDATOR_URL") else "settings",
    }


@router.put("/admin/settings/fsv-url")
async def set_fsv_url_setting(
    body: _FsvUrlRequest,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, object]:
    """Set or clear the FSV base URL. Requires admin role.

    Setting an empty string or null clears the persisted URL (env var still
    takes precedence when present).
    """
    url = (body.url or "").strip() or None
    settings_manager.update_setting("fsv_url", url)
    return {"url": url, "configured": bool(url)}
