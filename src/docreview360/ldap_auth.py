# SPDX-License-Identifier: MIT
"""LDAP/Active Directory authentication provider for DocReview360.

Configuration (environment variables)
--------------------------------------
LDAP_ENABLED          Set to "true" to activate LDAP authentication.
LDAP_URL              LDAP server URL, e.g. ldaps://ldap.example.com:636
LDAP_BIND_DN          Service account DN for directory searches,
                      e.g. CN=svc-docreview,OU=ServiceAccounts,DC=example,DC=com
LDAP_BIND_PASSWORD    Password for the service account.
LDAP_USER_BASE        Base DN to search for users,
                      e.g. OU=Users,DC=example,DC=com
LDAP_USER_FILTER      LDAP filter template with {username} placeholder,
                      e.g. (sAMAccountName={username})   [default]
LDAP_GROUP_BASE       Base DN to search for group membership (optional)
LDAP_GROUP_FILTER     Group filter with {user_dn} placeholder (optional),
                      e.g. (member={user_dn})
LDAP_ROLE_MAP         JSON mapping from LDAP group CN to DocReview360 role,
                      e.g. {"DocReview-Admins": "admin", "DocReview-Auditors": "auditor"}
LDAP_TLS_CA_CERT      Path to CA certificate file for LDAPS verification (optional)
LDAP_TIMEOUT          Connection timeout in seconds (default: 10)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)

try:
    import ldap3
    from ldap3 import Connection, Server, Tls
    from ldap3.core.exceptions import LDAPException

    _LDAP3_AVAILABLE = True
except ImportError:  # pragma: no cover — ldap extra not installed
    ldap3 = None  # type: ignore[assignment]
    Connection = None  # type: ignore[assignment]
    Server = None  # type: ignore[assignment]
    Tls = None  # type: ignore[assignment]
    LDAPException = Exception  # type: ignore[assignment,misc]
    _LDAP3_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

_DEFAULT_USER_FILTER = "(sAMAccountName={username})"
_DEFAULT_TIMEOUT = 10


def ldap_enabled() -> bool:
    """Return True if LDAP authentication is enabled via environment variable."""
    return os.getenv("LDAP_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _get_config() -> dict[str, Any]:
    """Return LDAP configuration from environment variables."""
    return {
        "url": os.getenv("LDAP_URL", ""),
        "bind_dn": os.getenv("LDAP_BIND_DN", ""),
        "bind_password": os.getenv("LDAP_BIND_PASSWORD", ""),
        "user_base": os.getenv("LDAP_USER_BASE", ""),
        "user_filter": os.getenv("LDAP_USER_FILTER", _DEFAULT_USER_FILTER),
        "group_base": os.getenv("LDAP_GROUP_BASE", ""),
        "group_filter": os.getenv("LDAP_GROUP_FILTER", ""),
        "role_map_raw": os.getenv("LDAP_ROLE_MAP", "{}"),
        "tls_ca_cert": os.getenv("LDAP_TLS_CA_CERT", ""),
        "timeout": int(os.getenv("LDAP_TIMEOUT", str(_DEFAULT_TIMEOUT))),
    }


def _parse_role_map(raw: str) -> dict[str, str]:
    """Parse LDAP_ROLE_MAP JSON string into a dict, returning {} on error."""
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return {str(k): str(v) for k, v in result.items()}
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        _logger.warning("LDAP_ROLE_MAP is invalid JSON: %s", exc)
    return {}


def _build_server(url: str, tls_ca_cert: str, timeout: int) -> Any:
    """Build an ldap3 Server object from a URL, optionally with TLS."""
    if not _LDAP3_AVAILABLE:
        raise ImportError(
            "ldap3 is required for LDAP authentication. "
            "Install it with: pip install 'docreview360[ldap]'"
        )

    use_ssl = url.lower().startswith("ldaps://")
    tls = None
    if use_ssl:
        import ssl

        tls_kwargs: dict[str, Any] = {"validate": ssl.CERT_REQUIRED}
        if tls_ca_cert:
            tls_kwargs["ca_certs_file"] = tls_ca_cert
        tls = Tls(**tls_kwargs)

    return Server(url, use_ssl=use_ssl, tls=tls, connect_timeout=timeout)


# ---------------------------------------------------------------------------
# Core LDAP operations
# ---------------------------------------------------------------------------


def _find_user_dn(
    conn: Any,
    user_base: str,
    user_filter_tpl: str,
    username: str,
) -> str | None:
    """Search for a user DN in the directory.  Returns the DN or None."""
    ldap_filter = user_filter_tpl.format(username=_escape_ldap_filter(username))
    try:
        conn.search(
            search_base=user_base,
            search_filter=ldap_filter,
            attributes=["distinguishedName"],
        )
    except LDAPException as exc:
        _logger.warning("LDAP user search failed: %s", exc)
        return None

    entries = conn.entries
    if not entries:
        return None
    dn = entries[0].entry_dn
    return str(dn) if dn else None


def _escape_ldap_filter(value: str) -> str:
    """Escape special characters in an LDAP filter value per RFC 4515."""
    replacements = [
        ("\\", "\\5c"),
        ("*", "\\2a"),
        ("(", "\\28"),
        (")", "\\29"),
        ("\x00", "\\00"),
    ]
    for char, escaped in replacements:
        value = value.replace(char, escaped)
    return value


def authenticate_ldap(username: str, password: str) -> str | None:
    """Try to bind to LDAP as the given user.

    Returns the username on success, or None if authentication fails.

    The function:
    1. Binds with the service account to locate the user's DN.
    2. Attempts a bind with the user's own DN and password to verify credentials.
    """
    if not username or not password:
        return None

    if not _LDAP3_AVAILABLE:
        _logger.error(
            "ldap3 is not installed — install with: pip install 'docreview360[ldap]'"
        )
        return None

    cfg = _get_config()
    if not cfg["url"] or not cfg["user_base"]:
        _logger.error("LDAP_URL and LDAP_USER_BASE must be set to use LDAP authentication")
        return None

    try:
        server = _build_server(cfg["url"], cfg["tls_ca_cert"], cfg["timeout"])

        # Step 1: bind with service account to search for the user
        service_conn = Connection(
            server,
            user=cfg["bind_dn"] or None,
            password=cfg["bind_password"] or None,
            authentication=ldap3.SIMPLE if cfg["bind_dn"] else ldap3.ANONYMOUS,
            auto_bind=True,
            receive_timeout=cfg["timeout"],
        )
        user_dn = _find_user_dn(
            service_conn,
            cfg["user_base"],
            cfg["user_filter"],
            username,
        )
        service_conn.unbind()

        if not user_dn:
            _logger.debug("LDAP: user %r not found in directory", username)
            return None

        # Step 2: bind as the user to verify password
        user_conn = Connection(
            server,
            user=user_dn,
            password=password,
            authentication=ldap3.SIMPLE,
            auto_bind=True,
            receive_timeout=cfg["timeout"],
        )
        user_conn.unbind()
        _logger.info("LDAP authentication successful for %r", username)
        return username

    except LDAPException as exc:
        _logger.debug("LDAP authentication failed for %r: %s", username, exc)
        return None
    except Exception as exc:  # noqa: BLE001 — unexpected errors must not crash the login flow
        _logger.error("Unexpected LDAP error for %r: %s", username, exc)
        return None


def get_ldap_groups(username: str) -> list[str]:
    """Return the list of LDAP group CNs for the given user.

    Returns an empty list if group lookup is not configured or fails.
    """
    if not _LDAP3_AVAILABLE:
        return []

    cfg = _get_config()
    group_base = cfg["group_base"]
    group_filter_tpl = cfg["group_filter"]

    if not group_base or not group_filter_tpl:
        return []

    try:
        server = _build_server(cfg["url"], cfg["tls_ca_cert"], cfg["timeout"])

        # Bind with service account to search for the user DN first
        service_conn = Connection(
            server,
            user=cfg["bind_dn"] or None,
            password=cfg["bind_password"] or None,
            authentication=ldap3.SIMPLE if cfg["bind_dn"] else ldap3.ANONYMOUS,
            auto_bind=True,
            receive_timeout=cfg["timeout"],
        )
        user_dn = _find_user_dn(
            service_conn,
            cfg["user_base"],
            cfg["user_filter"],
            username,
        )

        if not user_dn:
            service_conn.unbind()
            return []

        escaped_dn = _escape_ldap_filter(user_dn)
        group_filter = group_filter_tpl.format(user_dn=escaped_dn)

        try:
            service_conn.search(
                search_base=group_base,
                search_filter=group_filter,
                attributes=["cn"],
            )
            entries = service_conn.entries
            groups = [str(entry.cn) for entry in entries if hasattr(entry, "cn")]
        except LDAPException as exc:
            _logger.warning("LDAP group search failed for %r: %s", username, exc)
            groups = []
        finally:
            service_conn.unbind()

        return groups

    except LDAPException as exc:
        _logger.warning("LDAP group lookup failed for %r: %s", username, exc)
        return []
    except Exception as exc:  # noqa: BLE001
        _logger.error("Unexpected LDAP group lookup error for %r: %s", username, exc)
        return []


def map_ldap_groups_to_roles(groups: list[str]) -> list[str]:
    """Map LDAP group CNs to DocReview360 roles using LDAP_ROLE_MAP.

    Returns a deduplicated list of role names.  Groups not present in the
    mapping are silently ignored.
    """
    cfg = _get_config()
    role_map = _parse_role_map(cfg["role_map_raw"])
    roles: list[str] = []
    for group_cn in groups:
        role = role_map.get(group_cn)
        if role and role not in roles:
            roles.append(role)
    return roles


def ldap_login(username: str, password: str) -> tuple[str, list[str]] | None:
    """Authenticate via LDAP and return (username, roles) or None on failure.

    This is the primary entry point for the login flow integration.
    It combines authenticate_ldap, get_ldap_groups, and map_ldap_groups_to_roles.
    """
    authed = authenticate_ldap(username, password)
    if authed is None:
        return None

    groups = get_ldap_groups(authed)
    roles = map_ldap_groups_to_roles(groups)
    return authed, roles
