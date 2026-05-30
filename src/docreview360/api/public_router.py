# SPDX-License-Identifier: MIT
"""Public metadata endpoints extracted from api.__init__."""

from __future__ import annotations

import base64
import binascii
import logging
import os
import re
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth
from .. import config as config_module
from ..config import Config
from ..rbac import get_roles

_logger = logging.getLogger(__name__)

router = APIRouter()

_ALLOWED_BRANDING_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_ALLOWED_BRANDING_DATA_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/svg+xml",
}
_MAX_BRANDING_LOGO_BYTES = max(
    1,
    int(os.environ.get("DOCREVIEW360_BRANDING_MAX_LOGO_BYTES", str(256 * 1024))),
)


class BrandingPayload(BaseModel):
    """Public branding and build metadata consumed by the frontend shell."""

    branding_company_name: str
    branding_logo_url: str | None = None
    branding_logo_alt: str
    branding_support_url: str
    branding_docs_url: str
    branding_security_url: str
    branding_privacy_url: str
    branding_primary_color: str | None = None
    branding_accent_color: str | None = None
    branding_sidebar_bg: str | None = None
    branding_sidebar_text: str | None = None
    release_version: str
    release_build_number: str
    release_build_date: str
    release_commit: str | None = None
    environment: str


def _is_valid_branding_href(value: str) -> bool:
    """Return whether ``value`` is a safe local path or HTTP(S) URL."""

    candidate = value.strip()
    if not candidate:
        return False
    if candidate.startswith("/"):
        return True
    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_branding_logo_url(value: str | None) -> str | None:  # noqa: C901
    """Validate and normalize an optional branding logo URL or data URL."""

    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if len(candidate) > 600_000:
        raise ValueError("branding_logo_url is too large")

    if candidate.lower().startswith("data:"):
        match = re.match(r"^data:(image/[a-z0-9.+-]+);base64,(.+)$", candidate, re.IGNORECASE)
        if match is None:
            raise ValueError("branding_logo_url data URL must be base64 image data")
        mime = match.group(1).lower()
        if mime not in _ALLOWED_BRANDING_DATA_MIME_TYPES:
            raise ValueError("branding_logo_url data URL image type is not allowed")
        try:
            decoded = base64.b64decode(match.group(2), validate=True)
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
    if Path(parsed.path or "").suffix.lower() not in _ALLOWED_BRANDING_LOGO_EXTENSIONS:
        raise ValueError("branding_logo_url must use png, jpg, jpeg, webp, or svg")
    return candidate


def _load_release_version() -> str:
    """Return package version for footer metadata."""

    try:
        return importlib_metadata.version("docreview360")
    except importlib_metadata.PackageNotFoundError:
        return os.getenv("DOCREVIEW360_RELEASE_VERSION", "0.0.0-dev")


def get_branding_config_status() -> dict[str, str | bool | None]:
    """Return branding config health details for monitoring and diagnostics."""

    try:
        from ..branding import get_branding
        from ..db_store import get_db

        with get_db().orm_session() as db:
            branding = get_branding(db, "system")
        return {
            "loaded": True,
            "status": "ok",
            "error": None,
            "primary_color": branding.get("primary_color") or None,
            "accent_color": branding.get("accent_color") or None,
            "sidebar_bg": branding.get("sidebar_bg") or None,
            "sidebar_text": branding.get("sidebar_text") or None,
        }
    except Exception as exc:
        _logger.error("Failed to load branding configuration: %s", exc, exc_info=exc)
        return {
            "loaded": False,
            "status": "error",
            "error": str(exc),
            "primary_color": None,
            "accent_color": None,
            "sidebar_bg": None,
            "sidebar_text": None,
        }


def branding_payload_from_config(cfg: Config | None) -> BrandingPayload:
    """Build safe branding and release metadata for UI shell rendering."""

    active_cfg = cfg or Config(database="sqlite", editor="tiptap", cms="none", auth="local")
    try:
        logo_url = _normalize_branding_logo_url(active_cfg.branding_logo_url)
    except ValueError:
        logo_url = None

    def _safe_link(value: str, default: str) -> str:
        return value if _is_valid_branding_href(value) else default

    branding_status = get_branding_config_status()
    return BrandingPayload(
        branding_company_name=(active_cfg.branding_company_name or "DocReview360").strip()
        or "DocReview360",
        branding_logo_url=logo_url,
        branding_logo_alt=(active_cfg.branding_logo_alt or "Organization logo").strip()
        or "Organization logo",
        branding_support_url=_safe_link(active_cfg.branding_support_url, "/docs/"),
        branding_docs_url=_safe_link(active_cfg.branding_docs_url, "/docs/"),
        branding_security_url=_safe_link(active_cfg.branding_security_url, "/security"),
        branding_privacy_url=_safe_link(active_cfg.branding_privacy_url, "/privacy"),
        branding_primary_color=branding_status["primary_color"],
        branding_accent_color=branding_status["accent_color"],
        branding_sidebar_bg=branding_status["sidebar_bg"],
        branding_sidebar_text=branding_status["sidebar_text"],
        release_version=_load_release_version(),
        release_build_number=os.getenv("DOCREVIEW360_RELEASE_BUILD_NUMBER", "dev"),
        release_build_date=os.getenv("DOCREVIEW360_RELEASE_BUILD_DATE", "unknown"),
        release_commit=os.getenv("DOCREVIEW360_RELEASE_COMMIT"),
        environment=os.getenv("DOCREVIEW360_ENV", "dev") or "dev",
    )


def e2e_enabled() -> bool:
    return os.getenv("DOCREVIEW360_E2E_MODE") == "1"


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight health check endpoint used by the frontend."""

    return {"status": "ok"}


@router.post("/e2e/seed")
async def seed_e2e_endpoint() -> dict[str, Any]:
    """Reset and seed deterministic data for E2E runs."""

    if not e2e_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    from ..e2e_seed import seed_e2e_data

    return seed_e2e_data()


@router.get("/branding", response_model=BrandingPayload)
async def branding_endpoint() -> BrandingPayload:
    """Return public branding and release metadata for UI shell components."""

    return branding_payload_from_config(Config.load(config_module.CONFIG_FILE))


@router.get("/users/me")
async def current_user_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return information about the current user."""

    roles = list(get_roles(current_user.username))
    cfg = Config.load(config_module.CONFIG_FILE)
    inactivity_timeout = cfg.inactivity_timeout_minutes if cfg is not None else 30
    branding = branding_payload_from_config(cfg)
    return {
        "username": current_user.username,
        "is_admin": "admin" in roles,
        "active": auth.is_active(current_user.username),
        "roles": roles,
        "inactivity_timeout_minutes": inactivity_timeout,
        "branding_company_name": branding.branding_company_name,
        "branding_logo_url": branding.branding_logo_url,
        "branding_logo_alt": branding.branding_logo_alt,
        "release_version": branding.release_version,
        "release_build_number": branding.release_build_number,
        "release_build_date": branding.release_build_date,
        "release_commit": branding.release_commit,
        "environment": branding.environment,
    }
