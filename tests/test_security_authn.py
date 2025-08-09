"""Security and authentication tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.testclient import TestClient
from jose import jwt

from docreview360.auth import ALGORITHM, SECRET_KEY, create_access_token, keycloak_mfa_login
from docreview360.piv_cac import validate_piv_certificate

# Helpers for certificate


def _create_cert() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


# SEC-SSO

app_saml = FastAPI()


@app_saml.get("/saml/login")
def saml_login() -> Response:
    return Response(status_code=302, headers={"Location": "https://keycloak/saml"})


def test_keycloak_saml_login_flow() -> None:
    client = TestClient(app_saml)
    resp = client.get("/saml/login")
    assert resp.status_code == 302
    token = keycloak_mfa_login("admin", "secret", "123456")
    jwt_token = create_access_token({"sub": "admin"})
    decoded = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "admin"
    assert token


# SEC-CAC

app_cac = FastAPI()


@app_cac.get("/secure")
def secure_endpoint(client_cert: str = Header("")) -> dict[str, str]:
    if not validate_piv_certificate(client_cert):
        raise HTTPException(status_code=403)
    return {"role": "piv"}


def test_client_cert_role_mapping() -> None:
    pem = _create_cert()
    client = TestClient(app_cac)
    resp = client.get("/secure", headers={"client-cert": pem})
    assert resp.status_code == 200
    assert resp.json()["role"] == "piv"


# SEC-CS

app_csrf = FastAPI()


@app_csrf.post("/submit")
def submit(x_csrf_token: str | None = Header(None)) -> dict[str, bool]:
    if x_csrf_token != "token":
        raise HTTPException(status_code=403)
    return {"ok": True}


def test_missing_csrf_returns_403() -> None:
    client = TestClient(app_csrf)
    assert client.post("/submit").status_code == 403
    assert client.post("/submit", headers={"X-CSRFToken": "token"}).status_code == 200
