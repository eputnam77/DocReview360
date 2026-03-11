# SPDX-License-Identifier: MIT
"""White-label branding and terminology overrides.

Branding settings are stored in the ``OrgConfig`` table under the
``branding.*`` key namespace so they participate in the standard
hierarchical-config resolution chain.

Each organisation can override:
- ``branding.company_name``       — name shown in page titles and emails
- ``branding.logo_url``           — absolute/relative URL to org logo
- ``branding.logo_alt``           — accessible alt text for the logo
- ``branding.primary_color``      — CSS hex colour for primary UI elements
- ``branding.accent_color``       — CSS hex colour for accent elements
- ``branding.favicon_url``        — URL of the favicon
- ``branding.support_url``        — help/support link
- ``branding.docs_url``           — documentation link
- ``branding.privacy_url``        — privacy policy link
- ``branding.security_url``       — security disclosure link
- ``branding.locale``             — default UI locale for this org

Terminology overrides let orgs rename built-in concepts, e.g. calling
"Projects" "Cases" or "Documents" "Records":
- ``terminology.project``         — singular form, e.g. "Case"
- ``terminology.projects``        — plural form, e.g. "Cases"
- ``terminology.document``        — singular form, e.g. "Record"
- ``terminology.documents``       — plural form, e.g. "Records"
- ``terminology.approval``        — e.g. "Sign-off"
- ``terminology.reviewer``        — e.g. "Approver"
"""

from __future__ import annotations

import re
from typing import Any

_HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# ---------------------------------------------------------------------------
# Schema — default values and validators
# ---------------------------------------------------------------------------

BRANDING_DEFAULTS: dict[str, Any] = {
    "company_name": "DocReview360",
    "logo_url": None,
    "logo_alt": "Organization logo",
    "primary_color": "#2563eb",
    "accent_color": "#16a34a",
    "sidebar_bg": None,
    "sidebar_text": None,
    "favicon_url": "/favicon.ico",
    "support_url": "/docs/",
    "docs_url": "/docs/",
    "privacy_url": "/privacy",
    "security_url": "/security",
    "locale": "en",
}

TERMINOLOGY_DEFAULTS: dict[str, str] = {
    "project": "Project",
    "projects": "Projects",
    "document": "Document",
    "documents": "Documents",
    "approval": "Approval",
    "reviewer": "Reviewer",
}


def _validate_color(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _HEX_COLOR_RE.match(value):
        raise ValueError(f"Color must be a CSS hex value (#RGB or #RRGGBB), got: {value!r}")
    return value


def _validate_url(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if value and not (value.startswith("/") or value.startswith("http://") or value.startswith("https://")):
        raise ValueError(f"{field} must be an absolute path or http(s) URL")
    return value or None


# ---------------------------------------------------------------------------
# Public read API
# ---------------------------------------------------------------------------


def get_branding(db: Any, org_id: str) -> dict[str, Any]:
    """Return the effective branding config for *org_id*.

    Merges BRANDING_DEFAULTS with any org-level overrides stored under the
    ``branding.*`` keys in ``OrgConfig``.
    """
    from .hierarchical_config import get_org_config_all

    merged = get_org_config_all(db, org_id)
    result: dict[str, Any] = dict(BRANDING_DEFAULTS)
    for key in list(BRANDING_DEFAULTS):
        config_key = f"branding.{key}"
        if config_key in merged:
            result[key] = merged[config_key]
    return result


def get_terminology(db: Any, org_id: str) -> dict[str, str]:
    """Return the effective terminology overrides for *org_id*."""
    from .hierarchical_config import get_org_config_all

    merged = get_org_config_all(db, org_id)
    result: dict[str, str] = dict(TERMINOLOGY_DEFAULTS)
    for key in list(TERMINOLOGY_DEFAULTS):
        config_key = f"terminology.{key}"
        if config_key in merged:
            result[key] = str(merged[config_key])
    return result


def get_full_theme(db: Any, org_id: str) -> dict[str, Any]:
    """Return branding + terminology combined (convenient for the frontend)."""
    return {
        "org_id": org_id,
        "branding": get_branding(db, org_id),
        "terminology": get_terminology(db, org_id),
    }


# ---------------------------------------------------------------------------
# Public write API
# ---------------------------------------------------------------------------


def set_branding(db: Any, org_id: str, updated_by: str, **kwargs: Any) -> dict[str, Any]:
    """Persist branding overrides for *org_id*.

    Only keys present in *kwargs* are written; others are untouched.
    Raises ``ValueError`` on invalid colour or URL values.
    """
    from .hierarchical_config import set_org_config

    _validate_branding_payload(kwargs)

    for key, value in kwargs.items():
        if key not in BRANDING_DEFAULTS:
            raise ValueError(f"Unknown branding key: {key!r}")
        set_org_config(db, org_id, f"branding.{key}", value, updated_by=updated_by)

    return get_branding(db, org_id)


def set_terminology(db: Any, org_id: str, updated_by: str, **kwargs: str) -> dict[str, str]:
    """Persist terminology overrides for *org_id*.

    Only keys present in *kwargs* are written.
    """
    from .hierarchical_config import set_org_config

    for key, value in kwargs.items():
        if key not in TERMINOLOGY_DEFAULTS:
            raise ValueError(f"Unknown terminology key: {key!r}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"terminology.{key} must be a non-empty string")
        set_org_config(db, org_id, f"terminology.{key}", value.strip(), updated_by=updated_by)

    return get_terminology(db, org_id)


def reset_branding(db: Any, org_id: str, updated_by: str) -> dict[str, Any]:
    """Remove all branding overrides for *org_id*, reverting to system defaults."""
    from .hierarchical_config import delete_org_config

    for key in BRANDING_DEFAULTS:
        try:
            delete_org_config(db, org_id, f"branding.{key}")
        except Exception:
            pass
    return get_branding(db, org_id)


def reset_terminology(db: Any, org_id: str, updated_by: str) -> dict[str, str]:
    """Remove all terminology overrides for *org_id*, reverting to system defaults."""
    from .hierarchical_config import delete_org_config

    for key in TERMINOLOGY_DEFAULTS:
        try:
            delete_org_config(db, org_id, f"terminology.{key}")
        except Exception:
            pass
    return get_terminology(db, org_id)


# ---------------------------------------------------------------------------
# Internal validation
# ---------------------------------------------------------------------------


def _validate_branding_payload(data: dict[str, Any]) -> None:
    for color_key in ("primary_color", "accent_color", "sidebar_bg", "sidebar_text"):
        if color_key in data:
            data[color_key] = _validate_color(data[color_key])

    for url_key in ("logo_url", "favicon_url", "support_url", "docs_url", "privacy_url", "security_url"):
        if url_key in data:
            data[url_key] = _validate_url(data[url_key], url_key)

    if "company_name" in data:
        name = (data["company_name"] or "").strip()
        if not name:
            raise ValueError("company_name cannot be empty")
        data["company_name"] = name

    if "logo_alt" in data:
        data["logo_alt"] = (data["logo_alt"] or "").strip() or "Organization logo"

    if "locale" in data:
        from .i18n import SUPPORTED_LOCALES, _normalise
        data["locale"] = _normalise(data["locale"])
        if data["locale"] not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported locale: {data['locale']!r}")
