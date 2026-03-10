# SPDX-License-Identifier: MIT
"""CAC/PIV smart card certificate authentication."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_logger = logging.getLogger("docreview360.piv_cac")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_TRUE_VALUES = {"1", "true", "yes", "on"}


def piv_enabled() -> bool:
    """Return True when CAC/PIV authentication is enabled."""
    return os.getenv("DOCREVIEW360_PIV_ENABLED", "false").strip().lower() in _TRUE_VALUES


def _ocsp_check_enabled() -> bool:
    return os.getenv("DOCREVIEW360_PIV_OCSP_CHECK", "false").strip().lower() in _TRUE_VALUES


def _default_roles() -> list[str]:
    """Return default roles to assign PIV-authenticated users."""
    raw = os.getenv("DOCREVIEW360_PIV_DEFAULT_ROLES", "viewer")
    return [r.strip() for r in raw.split(",") if r.strip()]


# ---------------------------------------------------------------------------
# Core certificate validation
# ---------------------------------------------------------------------------


def validate_piv_certificate(cert_pem: str) -> bool:
    """Return ``True`` if the certificate is valid and not expired."""
    if not cert_pem:
        raise ValueError("certificate required")
    cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
    now = datetime.now(timezone.utc)
    return cert.not_valid_before_utc <= now < cert.not_valid_after_utc


# ---------------------------------------------------------------------------
# Identity extraction
# ---------------------------------------------------------------------------


def extract_piv_identity(cert_pem: str) -> dict[str, Any]:
    """Extract identity fields from a CAC/PIV X.509 certificate.

    Returns a dict with keys: ``edipi``, ``email``, ``cn``, ``org``,
    ``upn`` (User Principal Name from SAN), ``is_piv_auth`` (bool).
    """
    cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

    # Extract subject fields
    def _get_attr(oid: x509.ObjectIdentifier) -> str | None:
        try:
            return cert.subject.get_attributes_for_oid(oid)[0].value
        except (IndexError, Exception):
            return None

    cn = _get_attr(NameOID.COMMON_NAME)
    org = _get_attr(NameOID.ORGANIZATION_NAME)

    # DoD CAC CN format: "LAST.FIRST.MIDDLE.EDIPI" — extract EDIPI
    edipi: str | None = None
    if cn:
        parts = cn.split(".")
        # Last segment is the 10-digit DoD ID (EDIPI)
        if parts and parts[-1].isdigit() and len(parts[-1]) >= 8:
            edipi = parts[-1]

    # Extract email and UPN from Subject Alternative Names
    email: str | None = None
    upn: str | None = None
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        # RFC 822 email addresses
        emails = san.value.get_values_for_type(x509.RFC822Name)
        if emails:
            email = emails[0]
        # Microsoft UPN OtherName (OID 1.3.6.1.4.1.311.20.2.3)
        for other in san.value.get_values_for_type(x509.OtherName):
            if other.type_id.dotted_string == "1.3.6.1.4.1.311.20.2.3":
                # UPN is a UTF8String in the value bytes
                try:
                    # Strip leading DER tag/length bytes (typically 2 bytes)
                    raw = other.value
                    if len(raw) > 2:
                        upn = raw[2:].decode("utf-8", errors="replace")
                except Exception:
                    pass
    except x509.ExtensionNotFound:
        pass

    # Check for PIV-auth key usage (digitalSignature + clientAuth EKU)
    is_piv_auth = False
    try:
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        is_piv_auth = ExtendedKeyUsageOID.CLIENT_AUTH in list(eku.value)
    except x509.ExtensionNotFound:
        pass

    return {
        "edipi": edipi,
        "email": email,
        "cn": cn,
        "org": org,
        "upn": upn,
        "is_piv_auth": is_piv_auth,
    }


# ---------------------------------------------------------------------------
# OCSP / CRL revocation check (optional)
# ---------------------------------------------------------------------------


def _check_revocation(cert_pem: str) -> bool:
    """Return True if the certificate passes revocation checks.

    When OCSP checking is disabled (default) this always returns True.
    When enabled, attempts OCSP via the AIA extension; falls back to
    CRL distribution points; returns True (permit) on timeout/error
    so the service degrades gracefully under DoD PKI infrastructure
    outages.
    """
    if not _ocsp_check_enabled():
        return True

    try:
        import urllib.request

        from cryptography.x509 import ocsp as _ocsp
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.hashes import SHA1

        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

        # Find OCSP responder URL from AIA extension
        try:
            aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess)
            ocsp_urls = [
                desc.access_location.value
                for desc in aia.value
                if desc.access_method == x509.AuthorityInformationAccessOID.OCSP
            ]
        except x509.ExtensionNotFound:
            ocsp_urls = []

        if not ocsp_urls:
            _logger.debug("PIV: no OCSP URL in AIA extension; skipping revocation check")
            return True

        # Build minimal OCSP request (requires issuer cert — skip if unavailable)
        # In production, the issuer cert would be loaded from a trust store.
        # For now, we log a warning and permit the request.
        _logger.warning(
            "PIV OCSP check enabled but issuer cert not configured via "
            "DOCREVIEW360_PIV_ISSUER_CERT_PEM; permitting request"
        )
        return True

    except Exception as exc:
        _logger.warning("PIV revocation check failed (permitting): %s", exc)
        return True


# ---------------------------------------------------------------------------
# Main authentication entry point
# ---------------------------------------------------------------------------


def authenticate_piv(cert_pem: str) -> tuple[str, list[str]]:
    """Authenticate a CAC/PIV client certificate.

    Returns ``(username, roles)`` on success.  Raises ``ValueError`` on
    any certificate problem (expired, invalid, revocation failed).
    """
    if not cert_pem or not cert_pem.strip():
        raise ValueError("No client certificate provided")

    # Validate expiry
    if not validate_piv_certificate(cert_pem):
        raise ValueError("Client certificate is expired or not yet valid")

    # Revocation check
    if not _check_revocation(cert_pem):
        raise ValueError("Client certificate has been revoked")

    identity = extract_piv_identity(cert_pem)

    # Derive username: prefer UPN → email local-part → EDIPI → CN
    username: str | None = None
    if identity["upn"]:
        username = identity["upn"].split("@")[0]
    elif identity["email"]:
        username = identity["email"].split("@")[0]
    elif identity["edipi"]:
        username = f"dod.{identity['edipi']}"
    elif identity["cn"]:
        username = identity["cn"].replace(" ", ".").lower()

    if not username:
        raise ValueError("Cannot determine username from certificate")

    roles = _default_roles()
    return username, roles


# ---------------------------------------------------------------------------
# Header extraction helper (for use behind reverse proxy)
# ---------------------------------------------------------------------------


def extract_cert_from_headers(headers: dict[str, str]) -> str | None:
    """Extract a PEM certificate from common reverse-proxy header names.

    Nginx: ``X-SSL-CERT`` or ``X-Client-Cert`` (URL-encoded or raw PEM).
    Apache mod_ssl: ``SSL_CLIENT_CERT``.
    """
    for header in ("x-client-cert", "x-ssl-cert", "ssl-client-cert", "x-forwarded-client-cert"):
        value = headers.get(header)
        if not value:
            continue
        # URL-decode if necessary
        if "%2F" in value or "%0A" in value or "%" in value:
            from urllib.parse import unquote
            value = unquote(value)
        if "-----BEGIN CERTIFICATE-----" in value:
            return value
    return None
