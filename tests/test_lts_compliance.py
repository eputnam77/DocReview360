# SPDX-License-Identifier: MIT
"""Tests for Item 40 (line 278): Long-term digital signature compliance.

Covers:
- TimestampAuthority sandbox mode
- create_ltv_package (baseline and extended levels)
- serialize_ltv_package / deserialize_ltv_package round-trip
- is_serial_revoked_in_crl
- cache_ocsp_response / get_cached_ocsp_status
- attach_lts_package from signatures.py
- GET /signatures/{id}/ltv endpoint
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# TimestampAuthority — sandbox mode
# ---------------------------------------------------------------------------


class TestTimestampAuthoritySandbox:
    """TimestampAuthority with no TSA URL operates in sandbox mode."""

    def _tsa(self):
        from docreview360.integrations.signature.lts import TimestampAuthority

        return TimestampAuthority(tsa_url="", timeout_seconds=5)

    def test_sandbox_flag(self):
        tsa = self._tsa()
        assert tsa._sandbox is True

    def test_request_returns_token(self):
        tsa = self._tsa()
        data = b"hello world"
        token = tsa.request_timestamp(data)
        assert token.tsa_name == "sandbox"
        assert token.serial_number >= 1
        assert len(token.token_der) > 0

    def test_message_imprint_is_sha256(self):
        tsa = self._tsa()
        data = b"document content"
        token = tsa.request_timestamp(data)
        expected = hashlib.sha256(data).digest()
        assert token.message_imprint == expected

    def test_gen_time_is_utc(self):
        tsa = self._tsa()
        token = tsa.request_timestamp(b"test")
        assert token.gen_time.tzinfo is not None

    def test_verify_timestamp_correct_data(self):
        tsa = self._tsa()
        data = b"verify me"
        token = tsa.request_timestamp(data)
        assert tsa.verify_timestamp(token, data) is True

    def test_verify_timestamp_wrong_data(self):
        tsa = self._tsa()
        data = b"correct data"
        token = tsa.request_timestamp(data)
        assert tsa.verify_timestamp(token, b"wrong data") is False

    def test_serial_increments(self):
        tsa = self._tsa()
        t1 = tsa.request_timestamp(b"a")
        t2 = tsa.request_timestamp(b"b")
        assert t2.serial_number > t1.serial_number

    def test_sandbox_token_der_contains_imprint(self):
        tsa = self._tsa()
        data = b"check imprint in der"
        token = tsa.request_timestamp(data)
        # sandbox DER contains the first 8 bytes of SHA-256
        imprint_prefix = hashlib.sha256(data).digest()[:8]
        assert imprint_prefix in token.token_der

    def test_empty_tsa_url_is_sandbox(self):
        from docreview360.integrations.signature.lts import TimestampAuthority

        tsa = TimestampAuthority()
        assert tsa._sandbox is True

    def test_whitespace_tsa_url_is_sandbox(self):
        from docreview360.integrations.signature.lts import TimestampAuthority

        tsa = TimestampAuthority(tsa_url="   ")
        assert tsa._sandbox is True


# ---------------------------------------------------------------------------
# TimestampAuthority — non-sandbox mode (HTTP mocked)
# ---------------------------------------------------------------------------


class TestTimestampAuthorityLive:
    def test_falls_back_to_sandbox_on_http_error(self):
        import httpx
        from docreview360.integrations.signature.lts import TimestampAuthority

        tsa = TimestampAuthority(tsa_url="https://tsa.example.com/ts", timeout_seconds=5)
        assert tsa._sandbox is False

        with patch("httpx.post", side_effect=httpx.ConnectError("unreachable")):
            token = tsa.request_timestamp(b"data")
        # Falls back to sandbox
        assert token.tsa_name == "sandbox"

    def test_successful_http_response_used(self):
        from docreview360.integrations.signature.lts import TimestampAuthority

        # Construct a fake TSA response with a recognizable generalizedTime
        # tag 0x18, length 0x0f, value "20260101120000Z"
        fake_gen_time = b"\x18\x0f20260101120000Z"
        fake_response_bytes = b"\x30\x00\x00\x00" + fake_gen_time + b"\x00" * 4

        mock_resp = MagicMock()
        mock_resp.content = fake_response_bytes
        mock_resp.raise_for_status = MagicMock()

        tsa = TimestampAuthority(tsa_url="https://tsa.example.com/ts", timeout_seconds=5)

        with patch("httpx.post", return_value=mock_resp):
            token = tsa.request_timestamp(b"document")

        assert token.gen_time.year == 2026
        assert token.gen_time.month == 1
        assert token.gen_time.day == 1
        assert token.tsa_name == "https://tsa.example.com/ts"


# ---------------------------------------------------------------------------
# create_ltv_package — baseline level
# ---------------------------------------------------------------------------


class TestCreateLTVPackageBaseline:
    def test_baseline_has_timestamp(self):
        from docreview360.integrations.signature.lts import create_ltv_package

        pkg = create_ltv_package("sig-001", b"document content")
        assert pkg.timestamp_token is not None
        assert pkg.ltv_level == "baseline"

    def test_baseline_no_ocsp_no_crl(self):
        from docreview360.integrations.signature.lts import create_ltv_package

        pkg = create_ltv_package("sig-002", b"doc")
        assert len(pkg.ocsp_responses) == 0
        assert len(pkg.crl_infos) == 0

    def test_baseline_document_hash_is_sha256(self):
        from docreview360.integrations.signature.lts import create_ltv_package

        data = b"hash test document"
        pkg = create_ltv_package("sig-003", data)
        expected = hashlib.sha256(data).hexdigest()
        assert pkg.document_hash == expected

    def test_baseline_signature_id_stored(self):
        from docreview360.integrations.signature.lts import create_ltv_package

        pkg = create_ltv_package("sig-unique-abc", b"content")
        assert pkg.signature_id == "sig-unique-abc"

    def test_baseline_created_at_is_utc(self):
        from docreview360.integrations.signature.lts import create_ltv_package

        pkg = create_ltv_package("sig-004", b"time test")
        assert pkg.created_at.tzinfo is not None

    def test_baseline_without_cert_no_ocsp(self, monkeypatch):
        monkeypatch.setenv("LTS_DEFAULT_LEVEL", "extended")
        from docreview360.integrations.signature.lts import create_ltv_package

        # No certificate_pem provided — OCSP cannot be fetched
        pkg = create_ltv_package("sig-005", b"data", certificate_pem=None)
        assert len(pkg.ocsp_responses) == 0


# ---------------------------------------------------------------------------
# create_ltv_package — extended level
# ---------------------------------------------------------------------------


class TestCreateLTVPackageExtended:
    def test_extended_level_with_cert(self, monkeypatch):
        monkeypatch.setenv("LTS_DEFAULT_LEVEL", "extended")

        with patch(
            "docreview360.integrations.signature.lts.fetch_ocsp_status"
        ) as mock_fetch:
            from docreview360.integrations.signature.lts import OCSPStatus

            now = datetime.now(timezone.utc)
            mock_fetch.return_value = OCSPStatus(
                cert_serial="abc123",
                status="good",
                this_update=now,
                next_update=now + timedelta(hours=1),
                raw_response=b"",
            )
            from docreview360.integrations.signature.lts import create_ltv_package

            pkg = create_ltv_package(
                "sig-006",
                b"extended doc",
                certificate_pem="-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----",
                tsa_url="",
            )

        assert pkg.ltv_level == "extended"
        assert len(pkg.ocsp_responses) == 1
        assert pkg.ocsp_responses[0].status == "good"

    def test_extended_includes_timestamp(self, monkeypatch):
        monkeypatch.setenv("LTS_DEFAULT_LEVEL", "extended")
        with patch(
            "docreview360.integrations.signature.lts.fetch_ocsp_status"
        ) as mock_fetch:
            from docreview360.integrations.signature.lts import OCSPStatus

            now = datetime.now(timezone.utc)
            mock_fetch.return_value = OCSPStatus(
                cert_serial="def456",
                status="good",
                this_update=now,
                next_update=now + timedelta(hours=1),
                raw_response=b"",
            )
            from docreview360.integrations.signature.lts import create_ltv_package

            pkg = create_ltv_package(
                "sig-007",
                b"extended doc with ts",
                certificate_pem="-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----",
            )
        assert pkg.timestamp_token is not None


# ---------------------------------------------------------------------------
# serialize_ltv_package / deserialize_ltv_package round-trip
# ---------------------------------------------------------------------------


class TestLTVSerializationRoundTrip:
    def _make_package(self, sig_id: str = "sig-rt-001"):
        from docreview360.integrations.signature.lts import create_ltv_package

        return create_ltv_package(sig_id, b"round-trip content")

    def test_roundtrip_signature_id(self):
        from docreview360.integrations.signature.lts import (
            deserialize_ltv_package,
            serialize_ltv_package,
        )

        pkg = self._make_package("sig-rt-002")
        data = serialize_ltv_package(pkg)
        restored = deserialize_ltv_package(data)
        assert restored.signature_id == pkg.signature_id

    def test_roundtrip_document_hash(self):
        from docreview360.integrations.signature.lts import (
            deserialize_ltv_package,
            serialize_ltv_package,
        )

        pkg = self._make_package("sig-rt-003")
        data = serialize_ltv_package(pkg)
        restored = deserialize_ltv_package(data)
        assert restored.document_hash == pkg.document_hash

    def test_roundtrip_ltv_level(self):
        from docreview360.integrations.signature.lts import (
            deserialize_ltv_package,
            serialize_ltv_package,
        )

        pkg = self._make_package("sig-rt-004")
        data = serialize_ltv_package(pkg)
        restored = deserialize_ltv_package(data)
        assert restored.ltv_level == pkg.ltv_level

    def test_roundtrip_timestamp_token(self):
        from docreview360.integrations.signature.lts import (
            deserialize_ltv_package,
            serialize_ltv_package,
        )

        pkg = self._make_package("sig-rt-005")
        data = serialize_ltv_package(pkg)
        restored = deserialize_ltv_package(data)
        assert restored.timestamp_token is not None
        assert restored.timestamp_token.tsa_name == pkg.timestamp_token.tsa_name
        assert restored.timestamp_token.serial_number == pkg.timestamp_token.serial_number
        assert restored.timestamp_token.message_imprint == pkg.timestamp_token.message_imprint

    def test_roundtrip_created_at_preserves_tz(self):
        from docreview360.integrations.signature.lts import (
            deserialize_ltv_package,
            serialize_ltv_package,
        )

        pkg = self._make_package("sig-rt-006")
        data = serialize_ltv_package(pkg)
        restored = deserialize_ltv_package(data)
        # Both should be timezone-aware and equal in UTC
        assert restored.created_at.tzinfo is not None
        assert abs((restored.created_at - pkg.created_at).total_seconds()) < 1.0

    def test_serialized_dict_is_json_serializable(self):
        import json

        from docreview360.integrations.signature.lts import (
            create_ltv_package,
            serialize_ltv_package,
        )

        pkg = create_ltv_package("sig-json-001", b"json test")
        data = serialize_ltv_package(pkg)
        # Should not raise
        json_str = json.dumps(data)
        assert "sig-json-001" in json_str

    def test_roundtrip_with_no_timestamp(self):
        from docreview360.integrations.signature.lts import (
            LTVPackage,
            deserialize_ltv_package,
            serialize_ltv_package,
        )

        pkg = LTVPackage(
            signature_id="sig-no-ts",
            document_hash="abc123",
            timestamp_token=None,
            ocsp_responses=[],
            crl_infos=[],
            created_at=datetime.now(timezone.utc),
            ltv_level="baseline",
        )
        data = serialize_ltv_package(pkg)
        restored = deserialize_ltv_package(data)
        assert restored.timestamp_token is None
        assert restored.signature_id == "sig-no-ts"

    def test_roundtrip_with_ocsp_responses(self):
        from docreview360.integrations.signature.lts import (
            LTVPackage,
            OCSPStatus,
            TimestampToken,
            deserialize_ltv_package,
            serialize_ltv_package,
        )

        now = datetime.now(timezone.utc)
        ocsp = OCSPStatus(
            cert_serial="serial-xyz",
            status="good",
            this_update=now,
            next_update=now + timedelta(hours=1),
            raw_response=b"\x00\x01\x02",
        )
        token = TimestampToken(
            serial_number=42,
            message_imprint=b"\xff" * 32,
            gen_time=now,
            tsa_name="https://tsa.example.com",
            token_der=b"\x30\x00",
        )
        pkg = LTVPackage(
            signature_id="sig-ocsp-rt",
            document_hash="deadbeef",
            timestamp_token=token,
            ocsp_responses=[ocsp],
            crl_infos=[],
            created_at=now,
            ltv_level="extended",
        )
        data = serialize_ltv_package(pkg)
        restored = deserialize_ltv_package(data)
        assert len(restored.ocsp_responses) == 1
        assert restored.ocsp_responses[0].cert_serial == "serial-xyz"
        assert restored.ocsp_responses[0].raw_response == b"\x00\x01\x02"


# ---------------------------------------------------------------------------
# is_serial_revoked_in_crl
# ---------------------------------------------------------------------------


class TestCRLRevocationCheck:
    def _make_crl(self, serials: list[str]):
        from docreview360.integrations.signature.lts import CRLInfo

        return CRLInfo(
            issuer_name="Test CA",
            this_update=datetime.now(timezone.utc),
            next_update=datetime.now(timezone.utc) + timedelta(days=1),
            revoked_serials=frozenset(serials),
            raw_crl_bytes=b"",
        )

    def test_revoked_serial_returns_true(self):
        from docreview360.integrations.signature.lts import is_serial_revoked_in_crl

        crl = self._make_crl(["AABBCC", "112233"])
        assert is_serial_revoked_in_crl(crl, "AABBCC") is True

    def test_clean_serial_returns_false(self):
        from docreview360.integrations.signature.lts import is_serial_revoked_in_crl

        crl = self._make_crl(["AABBCC"])
        assert is_serial_revoked_in_crl(crl, "DDEEFF") is False

    def test_empty_crl_always_clean(self):
        from docreview360.integrations.signature.lts import is_serial_revoked_in_crl

        crl = self._make_crl([])
        assert is_serial_revoked_in_crl(crl, "anything") is False

    def test_multiple_serials(self):
        from docreview360.integrations.signature.lts import is_serial_revoked_in_crl

        serials = [f"SER{i:04d}" for i in range(100)]
        crl = self._make_crl(serials)
        assert is_serial_revoked_in_crl(crl, "SER0050") is True
        assert is_serial_revoked_in_crl(crl, "SER9999") is False


# ---------------------------------------------------------------------------
# OCSP cache
# ---------------------------------------------------------------------------


class TestOCSPCache:
    def _fresh_status(self, serial: str, status: str = "good") -> "OCSPStatus":
        from docreview360.integrations.signature.lts import OCSPStatus

        now = datetime.now(timezone.utc)
        return OCSPStatus(
            cert_serial=serial,
            status=status,  # type: ignore[arg-type]
            this_update=now,
            next_update=now + timedelta(hours=1),
            raw_response=b"",
        )

    def test_cache_and_retrieve(self):
        from docreview360.integrations.signature.lts import (
            _ocsp_cache,
            cache_ocsp_response,
            get_cached_ocsp_status,
        )

        serial = "test-cache-serial-001"
        _ocsp_cache.pop(serial, None)  # ensure clean state
        status = self._fresh_status(serial)
        cache_ocsp_response(serial, status)
        result = get_cached_ocsp_status(serial)
        assert result is not None
        assert result.status == "good"
        assert result.cert_serial == serial

    def test_miss_returns_none(self):
        from docreview360.integrations.signature.lts import get_cached_ocsp_status

        result = get_cached_ocsp_status("definitely-not-cached-xyz")
        assert result is None

    def test_expired_entry_returns_none(self):
        from docreview360.integrations.signature.lts import (
            OCSPStatus,
            _ocsp_cache,
            cache_ocsp_response,
            get_cached_ocsp_status,
        )

        serial = "expired-serial-999"
        _ocsp_cache.pop(serial, None)
        now = datetime.now(timezone.utc)
        expired = OCSPStatus(
            cert_serial=serial,
            status="good",
            this_update=now - timedelta(hours=2),
            next_update=now - timedelta(hours=1),  # already past
            raw_response=b"",
        )
        cache_ocsp_response(serial, expired)
        result = get_cached_ocsp_status(serial)
        assert result is None

    def test_no_next_update_cached_indefinitely(self):
        from docreview360.integrations.signature.lts import (
            OCSPStatus,
            _ocsp_cache,
            cache_ocsp_response,
            get_cached_ocsp_status,
        )

        serial = "no-next-update-serial"
        _ocsp_cache.pop(serial, None)
        status = OCSPStatus(
            cert_serial=serial,
            status="unknown",
            this_update=datetime.now(timezone.utc),
            next_update=None,
            raw_response=b"",
        )
        cache_ocsp_response(serial, status)
        result = get_cached_ocsp_status(serial)
        assert result is not None

    def test_overwrite_cached_entry(self):
        from docreview360.integrations.signature.lts import (
            _ocsp_cache,
            cache_ocsp_response,
            get_cached_ocsp_status,
        )

        serial = "overwrite-serial-001"
        _ocsp_cache.pop(serial, None)
        cache_ocsp_response(serial, self._fresh_status(serial, "good"))
        cache_ocsp_response(serial, self._fresh_status(serial, "revoked"))
        result = get_cached_ocsp_status(serial)
        assert result is not None
        assert result.status == "revoked"


# ---------------------------------------------------------------------------
# attach_lts_package / get_ltv_package in signatures.py
# ---------------------------------------------------------------------------


class TestAttachLTSPackage:
    def setup_method(self):
        """Clear the LTV package store before each test."""
        from docreview360.approvals import signatures as sig_mod

        sig_mod._ltv_packages.clear()

    def test_attach_creates_package(self):
        from docreview360.approvals.signatures import attach_lts_package, get_ltv_package

        pkg = attach_lts_package("sig-attach-001", b"document bytes")
        assert pkg is not None
        assert pkg.signature_id == "sig-attach-001"
        stored = get_ltv_package("sig-attach-001")
        assert stored is pkg

    def test_get_missing_returns_none(self):
        from docreview360.approvals.signatures import get_ltv_package

        assert get_ltv_package("nonexistent-sig-xyz") is None

    def test_attach_stores_correct_hash(self):
        from docreview360.approvals.signatures import attach_lts_package

        data = b"content for hashing"
        pkg = attach_lts_package("sig-attach-hash", data)
        expected_hash = hashlib.sha256(data).hexdigest()
        assert pkg.document_hash == expected_hash

    def test_attach_with_certificate(self):
        from docreview360.approvals.signatures import attach_lts_package

        pkg = attach_lts_package(
            "sig-attach-cert",
            b"doc with cert",
            certificate_pem="-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----",
        )
        assert pkg.signature_id == "sig-attach-cert"

    def test_attach_overwrites_previous(self):
        from docreview360.approvals.signatures import attach_lts_package, get_ltv_package

        attach_lts_package("sig-overwrite", b"first version")
        attach_lts_package("sig-overwrite", b"second version")
        pkg = get_ltv_package("sig-overwrite")
        expected = hashlib.sha256(b"second version").hexdigest()
        assert pkg.document_hash == expected

    def test_attach_returns_ltv_package_object(self):
        from docreview360.approvals.signatures import attach_lts_package
        from docreview360.integrations.signature.lts import LTVPackage

        pkg = attach_lts_package("sig-type-check", b"data")
        assert isinstance(pkg, LTVPackage)

    def test_package_level_is_baseline_by_default(self):
        from docreview360.approvals.signatures import attach_lts_package

        pkg = attach_lts_package("sig-baseline-default", b"data")
        assert pkg.ltv_level == "baseline"


# ---------------------------------------------------------------------------
# GET /signatures/{signature_id}/ltv endpoint
# ---------------------------------------------------------------------------


class TestGetLTVEndpoint:
    def _alice_headers(self, client):
        from docreview360 import auth, rbac

        try:
            auth.create_user("alice", "password")
        except Exception:
            pass
        rbac.add_role("alice", "admin")
        resp = client.post("/token", data={"username": "alice", "password": "password"})
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def setup_method(self):
        from docreview360.approvals import signatures as sig_mod

        sig_mod._ltv_packages.clear()

    def test_returns_404_when_no_package(self):
        from docreview360.api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/signatures/nonexistent-sig-abc/ltv", headers=headers)
        assert resp.status_code == 404
        body = resp.json()
        assert "LTV package not found" in (body.get("detail") or body.get("message", ""))

    def test_returns_ltv_package_json(self):
        from docreview360.api import app
        from docreview360.approvals.signatures import attach_lts_package
        from fastapi.testclient import TestClient

        attach_lts_package("sig-endpoint-001", b"endpoint test document")

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/signatures/sig-endpoint-001/ltv", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["signature_id"] == "sig-endpoint-001"
        assert "document_hash" in data
        assert "ltv_level" in data
        assert "timestamp_token" in data
        assert "created_at" in data

    def test_ltv_level_in_response(self):
        from docreview360.api import app
        from docreview360.approvals.signatures import attach_lts_package
        from fastapi.testclient import TestClient

        attach_lts_package("sig-endpoint-level", b"level check")

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/signatures/sig-endpoint-level/ltv", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ltv_level"] in ("baseline", "extended", "archival")

    def test_document_hash_matches_content(self):
        from docreview360.api import app
        from docreview360.approvals.signatures import attach_lts_package
        from fastapi.testclient import TestClient

        content = b"hash verification content"
        attach_lts_package("sig-endpoint-hash", content)
        expected_hash = hashlib.sha256(content).hexdigest()

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/signatures/sig-endpoint-hash/ltv", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["document_hash"] == expected_hash

    def test_requires_authentication(self):
        from docreview360.api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/signatures/some-sig/ltv")
        assert resp.status_code in (401, 403)

    def test_timestamp_token_present_in_response(self):
        from docreview360.api import app
        from docreview360.approvals.signatures import attach_lts_package
        from fastapi.testclient import TestClient

        attach_lts_package("sig-ts-check", b"timestamp content")

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/signatures/sig-ts-check/ltv", headers=headers)
        assert resp.status_code == 200
        ts = resp.json()["timestamp_token"]
        assert ts is not None
        assert "tsa_name" in ts
        assert "gen_time" in ts
        assert "serial_number" in ts


# ---------------------------------------------------------------------------
# create_archive_timestamp
# ---------------------------------------------------------------------------


class TestCreateArchiveTimestamp:
    def test_archive_timestamp_covers_package(self):
        from docreview360.integrations.signature.lts import (
            create_archive_timestamp,
            create_ltv_package,
        )

        pkg = create_ltv_package("sig-archive-001", b"archive document")
        archive_ts = create_archive_timestamp(pkg, tsa_url="")  # sandbox
        assert archive_ts is not None
        assert archive_ts.tsa_name == "sandbox"

    def test_archive_timestamp_imprint_differs_from_document(self):
        """The archive timestamp covers the LTV package, not the raw document."""
        import json

        from docreview360.integrations.signature.lts import (
            create_archive_timestamp,
            create_ltv_package,
            serialize_ltv_package,
        )

        doc = b"archive test document"
        pkg = create_ltv_package("sig-archive-002", doc)
        archive_ts = create_archive_timestamp(pkg, tsa_url="")

        # The imprint should be over the serialized package, not the raw document
        package_bytes = json.dumps(serialize_ltv_package(pkg), sort_keys=True).encode()
        expected_imprint = hashlib.sha256(package_bytes).digest()
        assert archive_ts.message_imprint == expected_imprint

        # Should differ from the raw document hash
        raw_imprint = hashlib.sha256(doc).digest()
        assert archive_ts.message_imprint != raw_imprint
