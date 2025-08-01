from __future__ import annotations

from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.backends import default_backend


def validate_piv_certificate(cert_pem: str) -> bool:
    """Return ``True`` if the certificate is valid and not expired."""
    if not cert_pem:
        raise ValueError("certificate required")
    cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
    # Use the timezone-aware property directly
    cert_time = cert.not_valid_after_utc
    return cert_time > datetime.now(timezone.utc)
