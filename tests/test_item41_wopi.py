# SPDX-License-Identifier: MIT
"""Item 41 — WOPI host integration tests.

Tests the WOPI host module (``docreview360.wopi``) and the WOPI API router
(``/wopi/…``) that enables Microsoft 365 co-authoring.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item41_wopi.py -v
"""

from __future__ import annotations

import os
from datetime import timedelta

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    from docreview360 import rbac

    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _alice_token() -> str:
    """Return a raw JWT access token for alice (used as WOPI access_token param)."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    return auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))


def _make_document(client: TestClient, content: str = "Hello WOPI world") -> str:
    """Upload a document and return its id."""
    headers = _alice_headers()
    resp = client.post(
        "/documents/import",
        files={"file": ("test.txt", content.encode(), "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Unit-level tests — wopi module
# ---------------------------------------------------------------------------


class TestWOPIModule:
    """Tests against the ``docreview360.wopi`` module functions directly."""

    def test_get_wopi_file_info_returns_correct_fields(self) -> None:
        """get_wopi_file_info returns a WOPICheckFileInfo with expected fields."""
        from docreview360.documents import import_document
        from docreview360.wopi import get_wopi_file_info, WOPICheckFileInfo

        doc = import_document("hello.txt", b"Hello from WOPI", user="alice")
        info = get_wopi_file_info(doc.id, "alice")

        assert isinstance(info, WOPICheckFileInfo)
        assert info.UserId == "alice"
        assert info.OwnerId == "alice"
        assert info.Size == len(b"Hello from WOPI")
        assert info.SupportsLocks is True
        assert info.SupportsUpdate is True
        assert info.UserCanWrite is True
        assert info.UserCanNotWriteRelative is True
        assert "docx" in info.BaseFileName

    def test_get_wopi_file_info_version_matches_document(self) -> None:
        """Version field matches document version_number."""
        from docreview360.documents import import_document
        from docreview360.wopi import get_wopi_file_info

        doc = import_document("ver.txt", b"initial", user="alice")
        info = get_wopi_file_info(doc.id, "alice")
        assert info.Version == str(doc.version_number)

    def test_get_wopi_file_info_missing_doc_raises_404(self) -> None:
        """get_wopi_file_info raises HTTPException 404 for missing doc."""
        from fastapi import HTTPException
        from docreview360.wopi import get_wopi_file_info

        with pytest.raises(HTTPException) as exc_info:
            get_wopi_file_info("nonexistent-doc-id", "alice")
        assert exc_info.value.status_code == 404

    def test_lock_unlock_cycle(self) -> None:
        """A lock can be acquired and then released with the correct token."""
        from docreview360.documents import import_document
        from docreview360.wopi import get_wopi_lock, set_wopi_lock, release_wopi_lock

        doc = import_document("lock.txt", b"lock test", user="alice")
        file_id = doc.id

        # No lock initially
        assert get_wopi_lock(file_id) is None

        # Acquire lock
        set_wopi_lock(file_id, "token-abc", "alice")
        lock = get_wopi_lock(file_id)
        assert lock is not None
        assert lock.lock_token == "token-abc"
        assert lock.locked_by == "alice"

        # Release lock
        release_wopi_lock(file_id, "token-abc")
        assert get_wopi_lock(file_id) is None

    def test_relock_same_token_succeeds(self) -> None:
        """Re-locking with the same token is a no-op (RefreshLock semantics)."""
        from docreview360.documents import import_document
        from docreview360.wopi import get_wopi_lock, set_wopi_lock

        doc = import_document("relock.txt", b"relock", user="alice")
        set_wopi_lock(doc.id, "token-same", "alice")
        # Same token again must not raise
        set_wopi_lock(doc.id, "token-same", "alice")
        lock = get_wopi_lock(doc.id)
        assert lock is not None
        assert lock.lock_token == "token-same"

    def test_relock_different_token_raises_409(self) -> None:
        """Re-locking with a different token raises HTTP 409."""
        from fastapi import HTTPException
        from docreview360.documents import import_document
        from docreview360.wopi import set_wopi_lock

        doc = import_document("conflict.txt", b"conflict", user="alice")
        set_wopi_lock(doc.id, "token-first", "alice")

        with pytest.raises(HTTPException) as exc_info:
            set_wopi_lock(doc.id, "token-second", "alice")
        assert exc_info.value.status_code == 409
        # Detail should be the existing lock token
        assert exc_info.value.detail == "token-first"

    def test_refresh_lock_updates_timestamp(self) -> None:
        """refresh_wopi_lock does not raise when token matches."""
        from docreview360.documents import import_document
        from docreview360.wopi import get_wopi_lock, refresh_wopi_lock, set_wopi_lock

        doc = import_document("refresh.txt", b"refresh", user="alice")
        set_wopi_lock(doc.id, "token-refresh", "alice")
        before = get_wopi_lock(doc.id)
        refresh_wopi_lock(doc.id, "token-refresh")
        after = get_wopi_lock(doc.id)
        assert after is not None
        assert after.locked_at >= before.locked_at  # type: ignore[operator]

    def test_put_file_contents_updates_document(self) -> None:
        """put_file_contents writes the bytes into the document store."""
        from docreview360.documents import get_document, import_document
        from docreview360.wopi import put_file_contents

        doc = import_document("put.txt", b"original text", user="alice")
        put_file_contents(doc.id, b"updated content", "alice")
        updated = get_document(doc.id)
        assert updated is not None
        assert "updated content" in updated.content


# ---------------------------------------------------------------------------
# API-level tests — WOPI router
# ---------------------------------------------------------------------------


class TestWOPIRouter:
    """Integration tests via the FastAPI test client."""

    def test_check_file_info_with_valid_token(self) -> None:
        """GET /wopi/files/{id} returns CheckFileInfo JSON."""
        client = TestClient(app)
        doc_id = _make_document(client)
        token = _alice_token()

        resp = client.get(f"/wopi/files/{doc_id}", params={"access_token": token})
        assert resp.status_code == 200
        data = resp.json()
        assert data["UserId"] == "alice"
        assert "BaseFileName" in data
        assert "Version" in data
        assert data["SupportsLocks"] is True

    def test_check_file_info_requires_valid_access_token(self) -> None:
        """GET /wopi/files/{id} returns 401 for an invalid token."""
        client = TestClient(app)
        doc_id = _make_document(client)

        resp = client.get(
            f"/wopi/files/{doc_id}",
            params={"access_token": "invalid.jwt.token"},
        )
        assert resp.status_code == 401

    def test_check_file_info_missing_token_returns_422(self) -> None:
        """GET /wopi/files/{id} returns 422 when access_token param is absent."""
        client = TestClient(app)
        doc_id = _make_document(client)

        resp = client.get(f"/wopi/files/{doc_id}")
        # FastAPI returns 422 for missing required query params
        assert resp.status_code == 422

    def test_lock_operation_sets_lock(self) -> None:
        """POST /wopi/files/{id} with X-WOPI-Override: LOCK sets a lock."""
        client = TestClient(app)
        doc_id = _make_document(client)
        token = _alice_token()

        resp = client.post(
            f"/wopi/files/{doc_id}",
            params={"access_token": token},
            headers={
                "X-WOPI-Override": "LOCK",
                "X-WOPI-Lock": "lock-token-001",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-WOPI-Lock") == "lock-token-001"

    def test_lock_operation_relock_same_token(self) -> None:
        """LOCK with same token (RefreshLock) returns 200."""
        client = TestClient(app)
        doc_id = _make_document(client)
        token = _alice_token()

        params = {"access_token": token}
        lock_headers = {"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "same-token"}

        resp1 = client.post(f"/wopi/files/{doc_id}", params=params, headers=lock_headers)
        assert resp1.status_code == 200

        resp2 = client.post(f"/wopi/files/{doc_id}", params=params, headers=lock_headers)
        assert resp2.status_code == 200

    def test_lock_operation_different_token_returns_409(self) -> None:
        """LOCK with a different token returns 409 with X-WOPI-Lock of existing token."""
        client = TestClient(app)
        doc_id = _make_document(client, content="Conflict test")
        token = _alice_token()

        params = {"access_token": token}
        resp1 = client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "first-token"},
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "second-token"},
        )
        assert resp2.status_code == 409
        assert resp2.headers.get("X-WOPI-Lock") == "first-token"

    def test_unlock_operation(self) -> None:
        """UNLOCK releases the lock and subsequent GET_LOCK returns empty token."""
        client = TestClient(app)
        doc_id = _make_document(client, content="Unlock test")
        token = _alice_token()
        params = {"access_token": token}

        # Lock
        client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "unlock-me"},
        )

        # Unlock
        resp_unlock = client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "UNLOCK", "X-WOPI-Lock": "unlock-me"},
        )
        assert resp_unlock.status_code == 200

        # Verify lock is gone via GET_LOCK
        resp_get = client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "GET_LOCK"},
        )
        assert resp_get.status_code == 200
        assert resp_get.headers.get("X-WOPI-Lock") == ""

    def test_get_lock_operation(self) -> None:
        """GET_LOCK returns the current lock token in X-WOPI-Lock header."""
        client = TestClient(app)
        doc_id = _make_document(client, content="GetLock test")
        token = _alice_token()
        params = {"access_token": token}

        # No lock yet
        resp_before = client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "GET_LOCK"},
        )
        assert resp_before.status_code == 200
        assert resp_before.headers.get("X-WOPI-Lock") == ""

        # Lock
        client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "get-lock-token"},
        )

        resp_after = client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "GET_LOCK"},
        )
        assert resp_after.status_code == 200
        assert resp_after.headers.get("X-WOPI-Lock") == "get-lock-token"

    def test_get_file_contents(self) -> None:
        """GET /wopi/files/{id}/contents returns document bytes."""
        client = TestClient(app)
        doc_id = _make_document(client, content="WOPI content bytes")
        token = _alice_token()

        resp = client.get(
            f"/wopi/files/{doc_id}/contents",
            params={"access_token": token},
        )
        assert resp.status_code == 200
        assert b"WOPI content bytes" in resp.content
        assert "X-WOPI-ItemVersion" in resp.headers

    def test_put_file_contents_updates_document(self) -> None:
        """POST /wopi/files/{id}/contents saves new content."""
        client = TestClient(app)
        doc_id = _make_document(client, content="Original content")
        token = _alice_token()
        params = {"access_token": token}

        # Lock first
        client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "put-lock"},
        )

        # PutFile
        resp = client.post(
            f"/wopi/files/{doc_id}/contents",
            params=params,
            headers={"X-WOPI-Lock": "put-lock"},
            content=b"Updated via WOPI PutFile",
        )
        assert resp.status_code == 200

        # Verify via GetFile
        resp_get = client.get(
            f"/wopi/files/{doc_id}/contents",
            params={"access_token": token},
        )
        assert b"Updated via WOPI PutFile" in resp_get.content

    def test_discovery_returns_xml(self) -> None:
        """GET /wopi/discovery returns valid WOPI discovery XML."""
        client = TestClient(app)
        resp = client.get("/wopi/discovery")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "xml" in content_type
        assert b"wopi-discovery" in resp.content
        assert b"docx" in resp.content
        assert b"xlsx" in resp.content
        assert b"pptx" in resp.content
        assert b"edit" in resp.content

    def test_refresh_lock_operation(self) -> None:
        """REFRESH_LOCK with matching token returns 200."""
        client = TestClient(app)
        doc_id = _make_document(client, content="Refresh test")
        token = _alice_token()
        params = {"access_token": token}

        client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "refresh-token"},
        )

        resp = client.post(
            f"/wopi/files/{doc_id}",
            params=params,
            headers={"X-WOPI-Override": "REFRESH_LOCK", "X-WOPI-Lock": "refresh-token"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-WOPI-Lock") == "refresh-token"

    def test_unknown_override_returns_501(self) -> None:
        """Unknown X-WOPI-Override value returns HTTP 501."""
        client = TestClient(app)
        doc_id = _make_document(client)
        token = _alice_token()

        resp = client.post(
            f"/wopi/files/{doc_id}",
            params={"access_token": token},
            headers={"X-WOPI-Override": "UNKNOWN_OP"},
        )
        assert resp.status_code == 501
