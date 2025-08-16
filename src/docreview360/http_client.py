from __future__ import annotations

import ssl

import httpx

# Shared TLS context enforcing TLS 1.2+ and certificate validation
_tls_context = ssl.create_default_context()
_tls_context.minimum_version = ssl.TLSVersion.TLSv1_2


def post(url: str, **kwargs: object) -> httpx.Response:
    """Send a POST request with TLS 1.2+ and certificate validation."""
    kwargs.setdefault("verify", _tls_context)
    return httpx.post(url, **kwargs)


def get(url: str, **kwargs: object) -> httpx.Response:
    """Send a GET request with TLS 1.2+ and certificate validation."""
    kwargs.setdefault("verify", _tls_context)
    return httpx.get(url, **kwargs)


def client(**kwargs: object) -> httpx.Client:
    """Return an HTTP client enforcing TLS 1.2+ and certificate validation."""
    kwargs.setdefault("verify", _tls_context)
    return httpx.Client(**kwargs)
