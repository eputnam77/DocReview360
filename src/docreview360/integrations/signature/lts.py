# SPDX-License-Identifier: MIT
"""Long-term digital signature compliance: RFC 3161 timestamps, LTV, OCSP, CRL.

This module provides:
- TimestampAuthority: RFC 3161 TSA client (sandbox mode when no TSA URL configured)
- OCSP response caching with TTL
- CRL (Certificate Revocation List) caching
- LTVPackage: Long-Term Validation package assembly and serialization
- create_archive_timestamp: archive timestamps over full LTV packages

Environment variables:
    LTS_TSA_URL                 TSA endpoint URL (empty = sandbox mode)
    LTS_TSA_TIMEOUT_SECONDS     HTTP timeout for TSA requests (default: 30)
    LTS_OCSP_CACHE_TTL_SECONDS  OCSP cache TTL in seconds (default: 3600)
    LTS_CRL_CACHE_TTL_SECONDS   CRL cache TTL in seconds (default: 86400)
    LTS_DEFAULT_LEVEL           LTV level: baseline/extended/archival (default: baseline)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variable helpers
# ---------------------------------------------------------------------------

_ENV_TSA_URL = "LTS_TSA_URL"
_ENV_TSA_TIMEOUT = "LTS_TSA_TIMEOUT_SECONDS"
_ENV_OCSP_TTL = "LTS_OCSP_CACHE_TTL_SECONDS"
_ENV_CRL_TTL = "LTS_CRL_CACHE_TTL_SECONDS"
_ENV_DEFAULT_LEVEL = "LTS_DEFAULT_LEVEL"

_VALID_LEVELS: frozenset[str] = frozenset({"baseline", "extended", "archival"})


def _get_tsa_url() -> str:
    return os.getenv(_ENV_TSA_URL, "").strip()


def _get_tsa_timeout() -> int:
    try:
        return int(os.getenv(_ENV_TSA_TIMEOUT, "30"))
    except (ValueError, TypeError):
        return 30


def _get_ocsp_cache_ttl() -> int:
    try:
        return int(os.getenv(_ENV_OCSP_TTL, "3600"))
    except (ValueError, TypeError):
        return 3600


def _get_crl_cache_ttl() -> int:
    try:
        return int(os.getenv(_ENV_CRL_TTL, "86400"))
    except (ValueError, TypeError):
        return 86400


def _get_default_level() -> Literal["baseline", "extended", "archival"]:
    raw = os.getenv(_ENV_DEFAULT_LEVEL, "baseline").strip().lower()
    if raw in _VALID_LEVELS:
        return raw  # type: ignore[return-value]
    return "baseline"


# ---------------------------------------------------------------------------
# RFC 3161 Timestamp Authority
# ---------------------------------------------------------------------------


@dataclass
class TimestampToken:
    """A parsed RFC 3161 timestamp token."""

    serial_number: int
    message_imprint: bytes  # SHA-256 hash of the signed data
    gen_time: datetime
    tsa_name: str
    token_der: bytes  # raw DER-encoded token (or mock bytes in sandbox mode)


def _build_minimal_ts_request(data: bytes) -> bytes:
    """Build a minimal DER-encoded TimeStampReq for the given data.

    This produces a best-effort minimal ASN.1 structure without requiring
    an external ASN.1 library.  The structure encodes:
        TimeStampReq ::= SEQUENCE {
            version          INTEGER { v1(1) },
            messageImprint   MessageImprint,
            nonce            INTEGER OPTIONAL,
            certReq          BOOLEAN DEFAULT FALSE
        }
        MessageImprint ::= SEQUENCE {
            hashAlgorithm    AlgorithmIdentifier,  -- SHA-256
            hashedMessage    OCTET STRING
        }
    """
    sha256_digest = hashlib.sha256(data).digest()

    # SHA-256 AlgorithmIdentifier OID: 2.16.840.1.101.3.4.2.1
    sha256_oid_bytes = bytes([
        0x06, 0x09,  # OID tag + length
        0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01,  # OID value
        0x05, 0x00,  # NULL parameters
    ])

    # AlgorithmIdentifier SEQUENCE
    alg_id = _der_sequence(sha256_oid_bytes)

    # HashedMessage OCTET STRING
    hashed_msg = _der_octet_string(sha256_digest)

    # MessageImprint SEQUENCE
    msg_imprint = _der_sequence(alg_id + hashed_msg)

    # version INTEGER { v1(1) }
    version = bytes([0x02, 0x01, 0x01])

    # certReq BOOLEAN TRUE (request signing certificate in response)
    cert_req = bytes([0x01, 0x01, 0xff])

    # TimeStampReq SEQUENCE
    ts_req = _der_sequence(version + msg_imprint + cert_req)
    return ts_req


def _der_sequence(content: bytes) -> bytes:
    return bytes([0x30]) + _der_length(len(content)) + content


def _der_octet_string(content: bytes) -> bytes:
    return bytes([0x04]) + _der_length(len(content)) + content


def _der_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    if n < 0x100:
        return bytes([0x81, n])
    if n < 0x10000:
        return bytes([0x82, (n >> 8) & 0xFF, n & 0xFF])
    # 3-byte length (sufficient for any practical payload here)
    return bytes([0x83, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])


def _parse_gen_time_from_response(response_bytes: bytes) -> datetime:
    """Extract the generalizedTime from a DER-encoded TSA response (best-effort).

    Searches for a 15-byte generalizedTime value (YYYYMMDDHHmmssZ) within the
    raw DER bytes.  Falls back to current UTC time if no match is found.
    """
    # GeneralizedTime is typically 15 bytes of ASCII digits + 'Z' encoded with
    # tag 0x18 (UNIVERSAL 24).  Search for the tag + length prefix.
    pattern = re.compile(rb"\x18\x0f(\d{14}Z)")
    match = pattern.search(response_bytes)
    if match:
        raw = match.group(1).decode("ascii")
        try:
            return datetime.strptime(raw, "%Y%m%d%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    # Also try with seconds fraction (17 bytes: YYYYMMDDHHmmss.sZ)
    pattern2 = re.compile(rb"\x18\x11(\d{14}\.\d{2}Z)")
    match2 = pattern2.search(response_bytes)
    if match2:
        raw2 = match2.group(1).decode("ascii")
        try:
            return datetime.strptime(raw2, "%Y%m%d%H%M%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _sandbox_token(data: bytes, serial: int) -> TimestampToken:
    """Create a mock timestamp token for sandbox/offline use."""
    imprint = hashlib.sha256(data).digest()
    now = datetime.now(timezone.utc)
    # Produce deterministic fake DER-like bytes
    token_der = b"\x30\x00\x00SANDBOX_TS:" + imprint[:8]
    return TimestampToken(
        serial_number=serial,
        message_imprint=imprint,
        gen_time=now,
        tsa_name="sandbox",
        token_der=token_der,
    )


_sandbox_serial_counter: int = 0


class TimestampAuthority:
    """RFC 3161 Timestamp Authority client.

    When ``tsa_url`` is empty or not provided, operates in sandbox mode and
    returns mock timestamp tokens without making any network requests.
    """

    def __init__(self, tsa_url: str = "", timeout_seconds: int = 30) -> None:
        self.tsa_url = tsa_url.strip()
        self.timeout_seconds = timeout_seconds
        self._sandbox = not self.tsa_url

    def request_timestamp(self, data: bytes) -> TimestampToken:
        """Request an RFC 3161 timestamp for ``data``.

        In sandbox mode, returns a mock token immediately.  Otherwise, POSTs a
        ``TimeStampReq`` to the configured TSA and parses the response.
        """
        global _sandbox_serial_counter

        if self._sandbox:
            _sandbox_serial_counter += 1
            return _sandbox_token(data, _sandbox_serial_counter)

        import httpx

        ts_req = _build_minimal_ts_request(data)
        try:
            response = httpx.post(
                self.tsa_url,
                content=ts_req,
                headers={
                    "Content-Type": "application/timestamp-query",
                    "Accept": "application/timestamp-reply",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:
            _logger.warning("TSA request to %r failed: %s — using sandbox fallback", self.tsa_url, exc)
            _sandbox_serial_counter += 1
            return _sandbox_token(data, _sandbox_serial_counter)

        token_der = response.content
        gen_time = _parse_gen_time_from_response(token_der)

        # Extract a serial number from the first few bytes (best-effort)
        serial = int.from_bytes(token_der[4:8], "big") if len(token_der) >= 8 else 0

        return TimestampToken(
            serial_number=serial,
            message_imprint=hashlib.sha256(data).digest(),
            gen_time=gen_time,
            tsa_name=self.tsa_url,
            token_der=token_der,
        )

    def verify_timestamp(self, token: TimestampToken, data: bytes) -> bool:
        """Verify that ``token`` covers ``data``.

        For sandbox tokens, compares the stored message imprint to the SHA-256
        of ``data``.  For real TSA tokens, performs the same imprint check
        (full chain validation requires cryptography library not required here).
        """
        expected = hashlib.sha256(data).digest()
        return token.message_imprint == expected


# ---------------------------------------------------------------------------
# OCSP response caching
# ---------------------------------------------------------------------------


@dataclass
class OCSPStatus:
    """Parsed OCSP response for a certificate."""

    cert_serial: str
    status: Literal["good", "revoked", "unknown"]
    this_update: datetime
    next_update: datetime | None
    raw_response: bytes


# In-memory OCSP cache: {cert_serial: OCSPStatus}
_ocsp_cache: dict[str, OCSPStatus] = {}


def fetch_ocsp_status(cert_pem: str, issuer_url: str) -> OCSPStatus:
    """Fetch OCSP status for the certificate identified by ``cert_pem``.

    Derives a best-effort serial number from the PEM hash when a proper
    X.509 parser is not available.  Returns an ``"unknown"`` status on any
    network or parse failure rather than raising.
    """
    cert_serial = hashlib.sha256(cert_pem.encode()).hexdigest()[:16]

    if issuer_url:
        import httpx

        try:
            response = httpx.get(issuer_url, timeout=10)
            raw = response.content
        except Exception as exc:
            _logger.warning("OCSP fetch from %r failed: %s", issuer_url, exc)
            raw = b""
    else:
        raw = b""

    now = datetime.now(timezone.utc)
    ttl = _get_ocsp_cache_ttl()

    # Without a full DER parser we cannot reliably determine revocation status
    # from raw OCSP response bytes; we default to "unknown" and store the
    # response for audit purposes.
    status: Literal["good", "revoked", "unknown"] = "unknown"
    if raw and b"good" in raw.lower():
        status = "good"
    elif raw and b"revoked" in raw.lower():
        status = "revoked"
    elif not raw:
        status = "unknown"

    import datetime as _dt

    next_update = now + _dt.timedelta(seconds=ttl)

    return OCSPStatus(
        cert_serial=cert_serial,
        status=status,
        this_update=now,
        next_update=next_update,
        raw_response=raw,
    )


def cache_ocsp_response(cert_serial: str, response: OCSPStatus) -> None:
    """Store ``response`` in the in-memory OCSP cache."""
    _ocsp_cache[cert_serial] = response


def get_cached_ocsp_status(cert_serial: str) -> OCSPStatus | None:
    """Return the cached OCSP status for ``cert_serial`` if still valid."""
    entry = _ocsp_cache.get(cert_serial)
    if entry is None:
        return None
    if entry.next_update is not None and datetime.now(timezone.utc) > entry.next_update:
        del _ocsp_cache[cert_serial]
        return None
    return entry


# ---------------------------------------------------------------------------
# CRL caching
# ---------------------------------------------------------------------------


@dataclass
class CRLInfo:
    """Parsed Certificate Revocation List metadata."""

    issuer_name: str
    this_update: datetime
    next_update: datetime
    revoked_serials: frozenset[str]
    raw_crl_bytes: bytes


# In-memory CRL cache: {crl_url: (CRLInfo, fetched_at)}
_crl_cache: dict[str, tuple[CRLInfo, datetime]] = {}


def fetch_crl(crl_url: str) -> CRLInfo:
    """Fetch and cache a CRL from ``crl_url``.

    Returns a ``CRLInfo`` with best-effort parsed fields.  On network failure
    returns an empty CRL (no revoked serials) rather than raising, so the
    caller can still assemble an LTV package.
    """
    ttl = _get_crl_cache_ttl()
    cached_entry = _crl_cache.get(crl_url)
    if cached_entry is not None:
        info, fetched_at = cached_entry
        import datetime as _dt

        if datetime.now(timezone.utc) < fetched_at + _dt.timedelta(seconds=ttl):
            return info

    raw = b""
    if crl_url:
        import httpx

        try:
            response = httpx.get(crl_url, timeout=15)
            raw = response.content
        except Exception as exc:
            _logger.warning("CRL fetch from %r failed: %s", crl_url, exc)

    now = datetime.now(timezone.utc)
    import datetime as _dt

    # Best-effort: extract issuer name from raw bytes via pattern search
    issuer_pattern = re.search(rb"\x0c([\x01-\x7f])([\x20-\x7e]+)", raw)
    issuer_name = issuer_pattern.group(2).decode("ascii", errors="replace") if issuer_pattern else crl_url

    info = CRLInfo(
        issuer_name=issuer_name,
        this_update=now,
        next_update=now + _dt.timedelta(seconds=ttl),
        revoked_serials=frozenset(),
        raw_crl_bytes=raw,
    )
    _crl_cache[crl_url] = (info, now)
    return info


def is_serial_revoked_in_crl(crl: CRLInfo, serial: str) -> bool:
    """Return ``True`` if ``serial`` appears in ``crl.revoked_serials``."""
    return serial in crl.revoked_serials


# ---------------------------------------------------------------------------
# LTV (Long-Term Validation) package
# ---------------------------------------------------------------------------


@dataclass
class LTVPackage:
    """Long-Term Validation package for a signed document."""

    signature_id: str
    document_hash: str  # SHA-256 hex of the signed document
    timestamp_token: TimestampToken | None
    ocsp_responses: list[OCSPStatus]
    crl_infos: list[CRLInfo]
    created_at: datetime
    ltv_level: Literal["baseline", "extended", "archival"]


def create_ltv_package(
    signature_id: str,
    document_bytes: bytes,
    certificate_pem: str | None = None,
    tsa_url: str | None = None,
) -> LTVPackage:
    """Create an LTV package for ``signature_id`` over ``document_bytes``.

    The ``ltv_level`` is determined by which evidence components are available:
    - ``"baseline"``:  timestamp only
    - ``"extended"``:  timestamp + OCSP
    - ``"archival"``:  timestamp + OCSP + CRL

    The ``LTS_DEFAULT_LEVEL`` environment variable caps the level that will be
    attempted (e.g. ``"baseline"`` skips OCSP and CRL even if cert is given).
    """
    resolved_tsa_url = tsa_url if tsa_url is not None else _get_tsa_url()
    default_level = _get_default_level()

    doc_hash = hashlib.sha256(document_bytes).hexdigest()
    now = datetime.now(timezone.utc)

    # --- Timestamp ---
    tsa = TimestampAuthority(tsa_url=resolved_tsa_url, timeout_seconds=_get_tsa_timeout())
    timestamp_token = tsa.request_timestamp(document_bytes)

    # --- OCSP (extended / archival only) ---
    ocsp_responses: list[OCSPStatus] = []
    if certificate_pem and default_level in ("extended", "archival"):
        try:
            ocsp_status = fetch_ocsp_status(certificate_pem, issuer_url="")
            cache_ocsp_response(ocsp_status.cert_serial, ocsp_status)
            ocsp_responses.append(ocsp_status)
        except Exception as exc:
            _logger.warning("OCSP fetch failed for LTV package: %s", exc)

    # --- CRL (archival only) ---
    crl_infos: list[CRLInfo] = []
    if certificate_pem and default_level == "archival":
        # In a real implementation we would extract CRL distribution points from
        # the certificate; here we store an empty CRL record as a placeholder.
        try:
            crl = fetch_crl(crl_url="")
            crl_infos.append(crl)
        except Exception as exc:
            _logger.warning("CRL fetch failed for LTV package: %s", exc)

    # Compute effective level
    if crl_infos and ocsp_responses:
        level: Literal["baseline", "extended", "archival"] = "archival"
    elif ocsp_responses:
        level = "extended"
    else:
        level = "baseline"

    return LTVPackage(
        signature_id=signature_id,
        document_hash=doc_hash,
        timestamp_token=timestamp_token,
        ocsp_responses=ocsp_responses,
        crl_infos=crl_infos,
        created_at=now,
        ltv_level=level,
    )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_timestamp_token(token: TimestampToken) -> dict:
    return {
        "serial_number": token.serial_number,
        "message_imprint": token.message_imprint.hex(),
        "gen_time": token.gen_time.isoformat(),
        "tsa_name": token.tsa_name,
        "token_der": token.token_der.hex(),
    }


def _deserialize_timestamp_token(data: dict) -> TimestampToken:
    return TimestampToken(
        serial_number=int(data["serial_number"]),
        message_imprint=bytes.fromhex(data["message_imprint"]),
        gen_time=datetime.fromisoformat(data["gen_time"]),
        tsa_name=data["tsa_name"],
        token_der=bytes.fromhex(data["token_der"]),
    )


def _serialize_ocsp_status(s: OCSPStatus) -> dict:
    return {
        "cert_serial": s.cert_serial,
        "status": s.status,
        "this_update": s.this_update.isoformat(),
        "next_update": s.next_update.isoformat() if s.next_update else None,
        "raw_response": s.raw_response.hex(),
    }


def _deserialize_ocsp_status(data: dict) -> OCSPStatus:
    return OCSPStatus(
        cert_serial=data["cert_serial"],
        status=data["status"],
        this_update=datetime.fromisoformat(data["this_update"]),
        next_update=datetime.fromisoformat(data["next_update"]) if data.get("next_update") else None,
        raw_response=bytes.fromhex(data["raw_response"]),
    )


def _serialize_crl_info(c: CRLInfo) -> dict:
    return {
        "issuer_name": c.issuer_name,
        "this_update": c.this_update.isoformat(),
        "next_update": c.next_update.isoformat(),
        "revoked_serials": sorted(c.revoked_serials),
        "raw_crl_bytes": c.raw_crl_bytes.hex(),
    }


def _deserialize_crl_info(data: dict) -> CRLInfo:
    return CRLInfo(
        issuer_name=data["issuer_name"],
        this_update=datetime.fromisoformat(data["this_update"]),
        next_update=datetime.fromisoformat(data["next_update"]),
        revoked_serials=frozenset(data.get("revoked_serials", [])),
        raw_crl_bytes=bytes.fromhex(data["raw_crl_bytes"]),
    )


def serialize_ltv_package(pkg: LTVPackage) -> dict:
    """Return a JSON-serializable dict representation of ``pkg``."""
    return {
        "signature_id": pkg.signature_id,
        "document_hash": pkg.document_hash,
        "timestamp_token": (
            _serialize_timestamp_token(pkg.timestamp_token)
            if pkg.timestamp_token is not None
            else None
        ),
        "ocsp_responses": [_serialize_ocsp_status(s) for s in pkg.ocsp_responses],
        "crl_infos": [_serialize_crl_info(c) for c in pkg.crl_infos],
        "created_at": pkg.created_at.isoformat(),
        "ltv_level": pkg.ltv_level,
    }


def deserialize_ltv_package(data: dict) -> LTVPackage:
    """Reconstruct an ``LTVPackage`` from a serialized dict."""
    ts_data = data.get("timestamp_token")
    return LTVPackage(
        signature_id=data["signature_id"],
        document_hash=data["document_hash"],
        timestamp_token=_deserialize_timestamp_token(ts_data) if ts_data else None,
        ocsp_responses=[_deserialize_ocsp_status(s) for s in data.get("ocsp_responses", [])],
        crl_infos=[_deserialize_crl_info(c) for c in data.get("crl_infos", [])],
        created_at=datetime.fromisoformat(data["created_at"]),
        ltv_level=data["ltv_level"],
    )


# ---------------------------------------------------------------------------
# Archive timestamp
# ---------------------------------------------------------------------------


def create_archive_timestamp(ltv_package: LTVPackage, tsa_url: str) -> TimestampToken:
    """Create an archive timestamp over the entire LTV package.

    The archive timestamp is computed over the canonical JSON serialization of
    the LTV package, providing a cryptographic commitment over all evidence
    (document hash, original timestamp, OCSP responses, CRLs) at archival time.
    """
    package_bytes = json.dumps(serialize_ltv_package(ltv_package), sort_keys=True).encode()
    tsa = TimestampAuthority(tsa_url=tsa_url, timeout_seconds=_get_tsa_timeout())
    return tsa.request_timestamp(package_bytes)
