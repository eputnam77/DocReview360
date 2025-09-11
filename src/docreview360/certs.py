from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Callable, Dict, Tuple
from urllib.parse import urlparse

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509 import ocsp
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

# cache of certificate URL -> certificate chain bytes
_chain_cache: Dict[str, bytes] = {}
# mapping of host -> expected sha256 fingerprint of certificate chain
_pinned_chains: Dict[str, str] = {}
# cache of CRL url -> (crl object, expires_at)
_crl_cache: Dict[str, Tuple[x509.CertificateRevocationList, datetime]] = {}
# cache of (ocsp url, serial) -> (status, expires_at)
_ocsp_cache: Dict[Tuple[str, int], Tuple[ocsp.OCSPCertStatus, datetime]] = {}


def register_pinned_chain(host: str, fingerprint: str) -> None:
    """Register expected ``fingerprint`` for ``host``.

    ``host`` names and certificate fingerprints may be supplied in mixed case.
    ``fetch_certificate`` normalises the host extracted from URLs to
    lowercase and computes fingerprints using ``hexdigest`` (which returns a
    lowercase string).  Without normalising the inputs here, registering a
    pinned chain with ``Example.COM`` or an uppercase fingerprint would fail
    lookup and trigger an ``untrusted certificate host`` or ``certificate
    chain mismatch`` error even though the values logically match.  Storing
    both pieces of information lower‑cased ensures comparisons are
    case‑insensitive and deterministic across platforms.
    """

    _pinned_chains[host.lower()] = fingerprint.lower()


def clear_cache() -> None:
    """Clear cached certificate chains (mainly for tests)."""

    _chain_cache.clear()
    _crl_cache.clear()
    _ocsp_cache.clear()


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

    host = (parsed.hostname or "").lower()
    pinned = _pinned_chains.get(host)
    if pinned is None:
        raise ValueError("untrusted certificate host")
    fingerprint = hashlib.sha256(data).hexdigest().lower()
    if fingerprint != pinned:
        raise ValueError("certificate chain mismatch")

    _chain_cache[url] = data
    return data


def verify_certificate_status(  # noqa: C901
    cert: x509.Certificate,
    *,
    issuer: x509.Certificate | None = None,
    fetcher: Callable[[str, bytes | None], bytes] | None = None,
) -> bool:
    """Return ``True`` if ``cert`` is not revoked according to CRL/OCSP data.

    ``issuer`` may be supplied to allow OCSP requests. ``fetcher`` can be used
    during tests to provide mocked network responses and receives the requested
    URL and optional POST payload.
    """

    now = datetime.now(timezone.utc)

    # Try OCSP first when issuer is available
    if issuer is not None:
        try:
            aia = cert.extensions.get_extension_for_oid(
                ExtensionOID.AUTHORITY_INFORMATION_ACCESS
            ).value
            ocsp_urls = [
                d.access_location.value
                for d in aia
                if d.access_method == AuthorityInformationAccessOID.OCSP
            ]
        except x509.ExtensionNotFound:
            ocsp_urls = []

        for url in ocsp_urls:
            cache_key = (url, cert.serial_number)
            cached = _ocsp_cache.get(cache_key)
            if cached and now < cached[1]:
                status = cached[0]
            else:
                builder = ocsp.OCSPRequestBuilder()
                builder = builder.add_certificate(cert, issuer, hashes.SHA1())
                req = builder.build()
                if fetcher is None:
                    resp = httpx.post(
                        url,
                        content=req.public_bytes(serialization.Encoding.DER),
                        headers={"Content-Type": "application/ocsp-request"},
                        timeout=5,
                    )
                    resp.raise_for_status()
                    data = resp.content
                else:
                    data = fetcher(url, req.public_bytes(serialization.Encoding.DER))
                ocsp_resp = ocsp.load_der_ocsp_response(data)
                if ocsp_resp.response_status != ocsp.OCSPResponseStatus.SUCCESSFUL:
                    return False
                single = next(iter(ocsp_resp.responses))
                next_update = getattr(single, "next_update_utc", None) or single.next_update
                if next_update is not None and next_update.tzinfo is None:
                    next_update = next_update.replace(tzinfo=timezone.utc)
                if next_update is None or next_update < now:
                    return False
                status = single.certificate_status
                _ocsp_cache[cache_key] = (status, next_update)
            if status == ocsp.OCSPCertStatus.REVOKED:
                return False
            if status == ocsp.OCSPCertStatus.GOOD:
                return True
        if ocsp_urls:
            # if OCSP URLs present but no good status was retrieved, fail closed
            return False

    # Fallback to CRL checking
    try:
        crl_dp = cert.extensions.get_extension_for_oid(ExtensionOID.CRL_DISTRIBUTION_POINTS).value
    except x509.ExtensionNotFound:
        crl_dp = None

    if crl_dp:
        crl_urls = []
        for dp in crl_dp:
            if dp.full_name is None:
                continue
            for name in dp.full_name:
                if isinstance(name, x509.UniformResourceIdentifier):
                    crl_urls.append(name.value)

        for url in crl_urls:
            cached = _crl_cache.get(url)
            if cached and now < cached[1]:
                crl = cached[0]
            else:
                if fetcher is None:
                    resp = httpx.get(url, timeout=5)
                    resp.raise_for_status()
                    data = resp.content
                else:
                    data = fetcher(url, None)
                try:
                    crl = x509.load_der_x509_crl(data)
                except ValueError:
                    crl = x509.load_pem_x509_crl(data)
                next_update = getattr(crl, "next_update_utc", None) or crl.next_update
                if next_update is not None and next_update.tzinfo is None:
                    next_update = next_update.replace(tzinfo=timezone.utc)
                if next_update is None or next_update < now:
                    return False
                _crl_cache[url] = (crl, next_update)
            for revoked in crl:
                if revoked.serial_number == cert.serial_number:
                    return False
            return True

    # No revocation information available
    return False


__all__ = [
    "fetch_certificate",
    "register_pinned_chain",
    "clear_cache",
    "verify_certificate_status",
]
