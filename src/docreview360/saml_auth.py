# SPDX-License-Identifier: MIT
"""SAML 2.0 Service Provider (SP) support for DocReview360.

DocReview360 acts as a SAML SP that delegates authentication to an external
Identity Provider (IdP).

Configuration (environment variables)
--------------------------------------
SAML_ENABLED          Set to "true" to activate SAML authentication.
SAML_SP_ENTITY_ID     This SP's Entity ID (usually the app URL),
                      e.g. https://docreview360.example.com
SAML_SP_ACS_URL       Assertion Consumer Service URL (callback after IdP auth),
                      e.g. https://docreview360.example.com/saml/acs
SAML_SP_SLS_URL       Single Logout Service URL (optional),
                      e.g. https://docreview360.example.com/saml/sls
SAML_IDP_ENTITY_ID    IdP's Entity ID from the IdP metadata.
SAML_IDP_SSO_URL      IdP's Single Sign-On URL.
SAML_IDP_SLO_URL      IdP's Single Logout URL (optional).
SAML_IDP_X509_CERT    IdP's X.509 signing certificate (PEM without headers).
SAML_SP_X509_CERT     This SP's X.509 certificate (PEM without headers, optional).
SAML_SP_PRIVATE_KEY   This SP's private key (PEM without headers, optional).
SAML_USERNAME_ATTR    SAML attribute containing the username
                      (default: NameID).
SAML_EMAIL_ATTR       SAML attribute containing the email (optional).
SAML_ROLE_ATTR        SAML attribute containing role(s) (optional).
SAML_ROLE_MAP         JSON mapping from IdP role value to DocReview360 role (optional).
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from typing import Any

_logger = logging.getLogger(__name__)

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.utils import OneLogin_Saml2_Utils

    _SAML_AVAILABLE = True
except ImportError:  # pragma: no cover — saml extra not installed
    OneLogin_Saml2_Auth = None  # type: ignore[assignment,misc]
    OneLogin_Saml2_Utils = None  # type: ignore[assignment,misc]
    _SAML_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def saml_enabled() -> bool:
    """Return True if SAML authentication is enabled via environment variable."""
    return os.getenv("SAML_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def get_saml_settings() -> dict[str, Any]:
    """Build and return the python3-saml settings dict from environment variables.

    This dict is passed directly to OneLogin_Saml2_Auth on each request.
    """
    sp_entity_id = os.getenv("SAML_SP_ENTITY_ID", "")
    sp_acs_url = os.getenv("SAML_SP_ACS_URL", "")
    sp_sls_url = os.getenv("SAML_SP_SLS_URL", "")
    sp_x509_cert = os.getenv("SAML_SP_X509_CERT", "")
    sp_private_key = os.getenv("SAML_SP_PRIVATE_KEY", "")

    idp_entity_id = os.getenv("SAML_IDP_ENTITY_ID", "")
    idp_sso_url = os.getenv("SAML_IDP_SSO_URL", "")
    idp_slo_url = os.getenv("SAML_IDP_SLO_URL", "")
    idp_x509_cert = os.getenv("SAML_IDP_X509_CERT", "")

    settings: dict[str, Any] = {
        "strict": True,
        "debug": os.getenv("DOCREVIEW360_ENV", "").lower() in {"dev", "development", "test"},
        "sp": {
            "entityId": sp_entity_id,
            "assertionConsumerService": {
                "url": sp_acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "x509cert": sp_x509_cert,
            "privateKey": sp_private_key,
        },
        "idp": {
            "entityId": idp_entity_id,
            "singleSignOnService": {
                "url": idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": idp_x509_cert,
        },
    }

    # Optional SP SLS
    if sp_sls_url:
        settings["sp"]["singleLogoutService"] = {
            "url": sp_sls_url,
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
        }

    # Optional IdP SLO
    if idp_slo_url:
        settings["idp"]["singleLogoutService"] = {
            "url": idp_slo_url,
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
        }

    return settings


def _build_saml_request(
    http_host: str,
    script_name: str,
    server_port: int,
    https: bool,
    post_data: dict[str, Any] | None = None,
    get_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the python3-saml request dict from raw request parameters."""
    return {
        "https": "on" if https else "off",
        "http_host": http_host,
        "script_name": script_name,
        "server_port": str(server_port),
        "get_data": get_data or {},
        "post_data": post_data or {},
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_auth_request(request_id: str | None = None) -> tuple[str, str]:
    """Initiate a SAML authentication flow.

    Returns (redirect_url, request_id).  The redirect_url should be sent to
    the browser.  The request_id can be used for response correlation.

    Raises RuntimeError if python3-saml is not installed or SAML is not configured.
    """
    if not _SAML_AVAILABLE:
        raise RuntimeError(
            "python3-saml is required for SAML authentication. "
            "Install it with: pip install 'docreview360[saml]'"
        )

    sp_acs_url = os.getenv("SAML_SP_ACS_URL", "")
    if not sp_acs_url:
        raise RuntimeError("SAML_SP_ACS_URL must be set to use SAML authentication")

    # Derive http_host and script_name from SP ACS URL
    from urllib.parse import urlparse

    parsed = urlparse(sp_acs_url)
    https = parsed.scheme == "https"
    http_host = parsed.netloc
    script_name = parsed.path.rsplit("/saml/acs", 1)[0] or "/"
    port = parsed.port or (443 if https else 80)

    req_dict = _build_saml_request(
        http_host=http_host,
        script_name=script_name,
        server_port=port,
        https=https,
    )

    settings = get_saml_settings()
    saml_auth = OneLogin_Saml2_Auth(req_dict, settings)

    req_id = request_id or secrets.token_urlsafe(16)
    redirect_url = saml_auth.login(return_to=None, force_authn=False, is_passive=False)

    return str(redirect_url), req_id


def process_saml_response(
    saml_response: str,
    request_id: str | None = None,
) -> dict[str, Any] | None:
    """Validate a SAML response POSTed by the IdP.

    Returns a dict of SAML attributes on success, or None on failure.

    The dict has keys:
    - ``name_id``: NameID value
    - ``attributes``: raw attribute dict from the SAML assertion
    - ``session_index``: session index (for SLO)
    """
    if not _SAML_AVAILABLE:
        _logger.error(
            "python3-saml is not installed — install with: pip install 'docreview360[saml]'"
        )
        return None

    sp_acs_url = os.getenv("SAML_SP_ACS_URL", "")
    if not sp_acs_url:
        _logger.error("SAML_SP_ACS_URL must be set to process SAML responses")
        return None

    from urllib.parse import urlparse

    parsed = urlparse(sp_acs_url)
    https = parsed.scheme == "https"
    http_host = parsed.netloc
    script_name = parsed.path.rsplit("/saml/acs", 1)[0] or "/"
    port = parsed.port or (443 if https else 80)

    req_dict = _build_saml_request(
        http_host=http_host,
        script_name=script_name,
        server_port=port,
        https=https,
        post_data={"SAMLResponse": saml_response},
    )

    settings = get_saml_settings()
    try:
        saml_auth = OneLogin_Saml2_Auth(req_dict, settings)
        saml_auth.process_response(request_id=request_id)
        errors = saml_auth.get_errors()
        if errors:
            _logger.warning(
                "SAML response validation errors: %s — %s",
                errors,
                saml_auth.get_last_error_reason(),
            )
            return None

        return {
            "name_id": saml_auth.get_nameid(),
            "attributes": saml_auth.get_attributes(),
            "session_index": saml_auth.get_session_index(),
        }
    except Exception as exc:  # noqa: BLE001 — SAML lib can raise varied exceptions
        _logger.warning("SAML response processing failed: %s", exc)
        return None


def extract_username(attributes: dict[str, Any]) -> str | None:
    """Extract the username from a SAML attribute dict returned by process_saml_response.

    Checks SAML_USERNAME_ATTR first; falls back to ``name_id``.
    """
    username_attr = os.getenv("SAML_USERNAME_ATTR", "")
    if username_attr:
        raw_attrs = attributes.get("attributes", {})
        values = raw_attrs.get(username_attr, [])
        if values:
            return str(values[0]).strip() or None

    # Fall back to NameID
    name_id = attributes.get("name_id")
    return str(name_id).strip() if name_id else None


def extract_roles(attributes: dict[str, Any]) -> list[str]:
    """Extract and map IdP role values from SAML attributes to DocReview360 roles.

    Returns a deduplicated list of role names.  If SAML_ROLE_ATTR is not set
    or the attribute is absent, returns an empty list.
    """
    role_attr = os.getenv("SAML_ROLE_ATTR", "")
    if not role_attr:
        return []

    raw_attrs = attributes.get("attributes", {})
    idp_roles: list[str] = [str(v) for v in raw_attrs.get(role_attr, [])]

    role_map_raw = os.getenv("SAML_ROLE_MAP", "{}")
    try:
        role_map: dict[str, str] = json.loads(role_map_raw) if role_map_raw else {}
        if not isinstance(role_map, dict):
            role_map = {}
    except (json.JSONDecodeError, TypeError, ValueError):
        role_map = {}

    roles: list[str] = []
    for idp_role in idp_roles:
        mapped = role_map.get(idp_role, idp_role)
        if mapped and mapped not in roles:
            roles.append(mapped)

    return roles


def get_sp_metadata() -> str:
    """Return the SP metadata XML string for registration with the IdP.

    Raises RuntimeError if python3-saml is not installed.
    """
    if not _SAML_AVAILABLE:
        raise RuntimeError(
            "python3-saml is required for SAML metadata generation. "
            "Install it with: pip install 'docreview360[saml]'"
        )

    sp_acs_url = os.getenv("SAML_SP_ACS_URL", "")
    if not sp_acs_url:
        raise RuntimeError("SAML_SP_ACS_URL must be set to generate SP metadata")

    from urllib.parse import urlparse

    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    parsed = urlparse(sp_acs_url)
    https = parsed.scheme == "https"
    http_host = parsed.netloc
    script_name = parsed.path.rsplit("/saml/acs", 1)[0] or "/"
    port = parsed.port or (443 if https else 80)

    req_dict = _build_saml_request(
        http_host=http_host,
        script_name=script_name,
        server_port=port,
        https=https,
    )

    settings = get_saml_settings()
    saml_settings = OneLogin_Saml2_Settings(settings=settings, sp_validation_only=True)
    metadata = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata)
    if errors:
        _logger.warning("SP metadata validation warnings: %s", errors)
    return metadata.decode("utf-8") if isinstance(metadata, bytes) else str(metadata)
