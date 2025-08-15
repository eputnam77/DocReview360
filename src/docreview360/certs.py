from __future__ import annotations

import hashlib
from typing import Callable, Dict
from urllib.parse import urlparse

import httpx

# cache of certificate URL -> certificate chain bytes
_chain_cache: Dict[str, bytes] = {}
# mapping of host -> expected sha256 fingerprint of certificate chain
_pinned_chains: Dict[str, str] = {}


def register_pinned_chain(host: str, fingerprint: str) -> None:
    """Register expected ``fingerprint`` for ``host``."""

    _pinned_chains[host] = fingerprint


def clear_cache() -> None:
    """Clear cached certificate chains (mainly for tests)."""

    _chain_cache.clear()


def fetch_certificate(url: str, *, fetcher: Callable[[str], bytes] | None = None) -> bytes:
    """Return certificate bytes for ``url`` ensuring HTTPS and pinned chain.

    When provided, ``fetcher`` is used instead of performing an HTTP request.
    Successful fetches are cached to avoid repeated network requests.
    """

    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("certificate URL must use HTTPS")
    if url in _chain_cache:
        return _chain_cache[url]
    if fetcher is None:
        resp = httpx.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.content
    else:
        data = fetcher(url)

    host = parsed.hostname or ""
    pinned = _pinned_chains.get(host)
    if not pinned:
        raise ValueError("untrusted certificate host")
    fingerprint = hashlib.sha256(data).hexdigest()
    if fingerprint != pinned:
        raise ValueError("certificate chain mismatch")

    _chain_cache[url] = data
    return data


__all__ = [
    "fetch_certificate",
    "register_pinned_chain",
    "clear_cache",
]
