from __future__ import annotations

import ssl

import httpx

# Shared TLS context enforcing TLS 1.2+ and certificate validation
_tls_context = ssl.create_default_context()
_tls_context.minimum_version = ssl.TLSVersion.TLSv1_2


def _ensure_tls(kwargs: dict) -> None:
    """Inject the shared TLS context unless a secure context is provided.

    Callers might attempt to disable certificate verification by passing
    ``verify=False``.  Using :func:`dict.setdefault` allowed that value to slip
    through, silently disabling TLS checks.  Instead we explicitly guard
    against falsey values so that verification cannot be turned off
    accidentally.  Custom :class:`ssl.SSLContext` instances are still honoured
    but upgraded to at least TLS 1.2 if necessary.
    """

    verify = kwargs.get("verify")
    if verify in (False, None):
        kwargs["verify"] = _tls_context
    elif isinstance(verify, ssl.SSLContext) and verify.minimum_version < ssl.TLSVersion.TLSv1_2:
        verify.minimum_version = ssl.TLSVersion.TLSv1_2


def post(url: str, **kwargs: object) -> httpx.Response:
    """Send a POST request with TLS 1.2+ and certificate validation."""
    _ensure_tls(kwargs)
    return httpx.post(url, **kwargs)


def get(url: str, **kwargs: object) -> httpx.Response:
    """Send a GET request with TLS 1.2+ and certificate validation."""
    _ensure_tls(kwargs)
    return httpx.get(url, **kwargs)


def client(**kwargs: object) -> httpx.Client:
    """Return an HTTP client enforcing TLS 1.2+ and certificate validation."""
    _ensure_tls(kwargs)
    return httpx.Client(**kwargs)
