import pytest
from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

from services import signature_verifier


@pytest.fixture
def auditor_client() -> TestClient:
    token = auth.create_access_token({"sub": "bob"})
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_verify_signature_endpoint_forbidden(auditor_client: TestClient) -> None:
    resp = auditor_client.get("/documents/foo/verify-signature")
    assert resp.status_code == 403


def test_verify_signature_stream_forbidden(auditor_client: TestClient) -> None:
    resp = auditor_client.get("/documents/foo/verify-signature/stream")
    assert resp.status_code == 403


def test_background_verification_forbidden() -> None:
    with pytest.raises(PermissionError):
        signature_verifier.verify_document_signatures.run(username="bob")  # type: ignore[attr-defined]
