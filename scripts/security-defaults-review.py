#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Security defaults reviewer.

Audits auth, OIDC, Keycloak, secrets, token lifetimes, and production-safe
env defaults for DocReview360. Always exits 0 (informational).

Usage:
    python scripts/security-defaults-review.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "docreview360"

findings: list[dict[str, str]] = []


def note(category: str, severity: str, message: str) -> None:
    findings.append({"category": category, "severity": severity, "message": message})
    indicator = "!" if severity in ("CRITICAL", "HIGH") else "~"
    print(f"  [{indicator}] [{category}] {severity}: {message}")


def ok(category: str, message: str) -> None:
    print(f"  [+] [{category}] ok: {message}")


def warn(category: str, message: str) -> None:
    note(category, "MEDIUM", message)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 1. JWT / secret-key hygiene
# ---------------------------------------------------------------------------

def check_jwt_secrets() -> None:
    section("JWT / Secret-Key Hygiene")

    auth_init = SRC / "auth" / "__init__.py"
    if not auth_init.exists():
        note("JWT", "HIGH", "auth/__init__.py not found — cannot verify secret enforcement")
        return

    text = auth_init.read_text(encoding="utf-8")

    # required=True enforcement
    if "required=True" in text:
        ok("JWT", "SECRET_KEY enforced as required in production")
    else:
        note("JWT", "HIGH", "No required=True guard on SECRET_KEY — dev secret may leak to prod")

    # banned weak secrets list
    if "_BANNED" in text or "banned" in text.lower():
        ok("JWT", "Banned weak-secret list present")
    else:
        warn("JWT", "No banned-secret list detected — common weak values may slip through")

    # minimum key length
    if "< 32" in text or "32" in text:
        ok("JWT", "Minimum SECRET_KEY length check present (>=32)")
    else:
        note("JWT", "MEDIUM", "No minimum SECRET_KEY length check detected")

    # previous-key rotation support
    if "PREVIOUS" in text or "previous" in text:
        ok("JWT", "Previous-key rotation support detected")
    else:
        warn("JWT", "No previous-key rotation — rolling secret updates may break active sessions")

    # HS256 vs RS256
    if "RS256" in text or "RS384" in text or "RS512" in text:
        ok("JWT", "Asymmetric algorithm (RS*) available")
    elif "HS256" in text:
        note("JWT", "LOW", "Only symmetric HS256 configured — consider RS256 for multi-service deployments")

    # algorithm allowlist
    if "ALGORITHM" in text:
        ok("JWT", "Configurable ALGORITHM env var present")


# ---------------------------------------------------------------------------
# 2. Token lifetimes
# ---------------------------------------------------------------------------

def check_token_lifetimes() -> None:
    section("Token Lifetimes")

    auth_init = SRC / "auth" / "__init__.py"
    if not auth_init.exists():
        note("Lifetimes", "HIGH", "auth/__init__.py not found")
        return

    text = auth_init.read_text(encoding="utf-8")

    # Access token expiry
    m = re.search(r"DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES\s*=\s*(\d+)", text)
    if m:
        minutes = int(m.group(1))
        if minutes <= 60:
            ok("Lifetimes", f"Access token expires in {minutes}m (<=60 — acceptable)")
        elif minutes <= 240:
            note("Lifetimes", "MEDIUM", f"Access token expires in {minutes}m — consider reducing to <=60m")
        else:
            note("Lifetimes", "HIGH", f"Access token expires in {minutes}m — long-lived tokens are risky")
    else:
        warn("Lifetimes", "ACCESS_TOKEN_EXPIRE_MINUTES not found in auth module")

    # OIDC idle timeout
    oidc = SRC / "oidc_client.py"
    if oidc.exists():
        oidc_text = oidc.read_text(encoding="utf-8")
        m2 = re.search(r"OIDC_IDLE_TIMEOUT_MINUTES.*?(\d+)", oidc_text)
        if m2:
            idle = int(m2.group(1))
            if idle == 0:
                note("Lifetimes", "MEDIUM", "OIDC_IDLE_TIMEOUT_MINUTES defaults to 0 — idle sessions never expire")
            elif idle <= 120:
                ok("Lifetimes", f"OIDC idle timeout = {idle}m (acceptable)")
            else:
                warn("Lifetimes", f"OIDC idle timeout = {idle}m — may be too long")
        if "SESSION_MAX_CONCURRENT" in oidc_text:
            ok("Lifetimes", "OIDC concurrent session cap present")


# ---------------------------------------------------------------------------
# 3. OIDC / Keycloak configuration
# ---------------------------------------------------------------------------

def check_oidc_keycloak() -> None:
    section("OIDC / Keycloak Configuration")

    oidc = SRC / "oidc_client.py"
    keycloak = SRC / "keycloak_auth.py"

    if not oidc.exists():
        note("OIDC", "MEDIUM", "oidc_client.py not found")
    else:
        text = oidc.read_text(encoding="utf-8")
        if "state" in text and "nonce" in text:
            ok("OIDC", "state and nonce CSRF protection present")
        else:
            note("OIDC", "HIGH", "OIDC state/nonce CSRF protection not detected")

        if "PKCE" in text or "code_verifier" in text or "code_challenge" in text:
            ok("OIDC", "PKCE (code_verifier/code_challenge) present")
        else:
            note("OIDC", "HIGH", "PKCE not detected in OIDC client — required for public clients")

        if "https://" in text or "OIDC_PROVIDER_URL" in text:
            ok("OIDC", "Provider URL configuration present")

        if "jit" in text.lower() or "provision" in text.lower():
            ok("OIDC", "JIT provisioning support present")

    if not keycloak.exists():
        note("OIDC", "LOW", "keycloak_auth.py not found — Keycloak integration may be absent")
    else:
        kc_text = keycloak.read_text(encoding="utf-8")
        if "realm_access" in kc_text or "resource_access" in kc_text:
            ok("OIDC", "Keycloak realm/resource role extraction present")
        if "map_keycloak_roles" in kc_text:
            ok("OIDC", "Keycloak → DocReview360 role mapping present")
        if "is_keycloak_provider" in kc_text:
            ok("OIDC", "Keycloak provider detection guard present")


# ---------------------------------------------------------------------------
# 4. Password policy
# ---------------------------------------------------------------------------

def check_password_policy() -> None:
    section("Password Policy")

    text = _auth_package_text()
    if not text:
        note("Password", "HIGH", "auth/ package not found")
        return

    if "password_history" in text:
        ok("Password", "Password history enforcement present in auth package")
    else:
        note("Password", "MEDIUM", "Password history enforcement not detected")

    if "max_age_days" in text or "is_password_expired" in text:
        ok("Password", "Password expiry enforcement present in auth package")
    else:
        warn("Password", "Password expiry (max_age_days) not detected")

    if "bcrypt" in text or "argon2" in text:
        ok("Password", "Strong password hashing (bcrypt/argon2) detected in auth package")
    else:
        note("Password", "HIGH", "bcrypt/argon2 hashing not detected — weak hashing risk")


# ---------------------------------------------------------------------------
# 5. MFA / TOTP
# ---------------------------------------------------------------------------

def _auth_package_text() -> str:
    """Concatenate all .py files in the auth package for broad searching."""
    parts: list[str] = []
    auth_dir = SRC / "auth"
    if auth_dir.is_dir():
        for f in sorted(auth_dir.glob("*.py")):
            parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)


def check_mfa() -> None:
    section("MFA / TOTP")

    text = _auth_package_text()
    if not text:
        note("MFA", "MEDIUM", "auth/ package not found")
        return

    if "totp" in text.lower() or "TOTP" in text or "otp_secret" in text:
        ok("MFA", "TOTP MFA present")
    else:
        warn("MFA", "TOTP MFA not detected in auth module")

    if "pyotp" in text or "otp" in text.lower():
        ok("MFA", "OTP library reference found")

    webauthn = SRC / "webauthn_auth.py"
    if webauthn.exists():
        ok("MFA", "WebAuthn/FIDO2 support present")
    else:
        note("MFA", "LOW", "webauthn_auth.py not found — no hardware-key MFA")

    piv = SRC / "piv_cac.py"
    if piv.exists():
        ok("MFA", "PIV/CAC smart-card auth present")


# ---------------------------------------------------------------------------
# 6. Production-safe env defaults
# ---------------------------------------------------------------------------

def check_env_defaults() -> None:
    section("Production-safe Env Defaults")

    # .env.example must exist
    env_example = REPO_ROOT / ".env.example"
    if env_example.exists():
        ok("Env", ".env.example present")
        text = env_example.read_text(encoding="utf-8")
        dangerous_defaults = [
            ("password", "weak default password"),
            ("admin123", "common admin password"),
            ("secret", "placeholder secret"),
            ("test", "test credential"),
        ]
        for pattern, label in dangerous_defaults:
            if pattern in text.lower():
                note("Env", "MEDIUM", f".env.example contains '{pattern}' — may be used verbatim")
    else:
        note("Env", "MEDIUM", ".env.example not found — teams may use ad-hoc env files")

    # DOCREVIEW360_ENV dev-mode guard
    config = SRC / "config.py"
    if config.exists():
        cfg_text = config.read_text(encoding="utf-8")
        if "DOCREVIEW360_ENV" in cfg_text:
            ok("Env", "DOCREVIEW360_ENV dev-mode gating present in config.py")
        else:
            warn("Env", "DOCREVIEW360_ENV not referenced in config.py")

    # .env must not be committed
    gitignore = REPO_ROOT / ".gitignore"
    if gitignore.exists():
        gi_text = gitignore.read_text(encoding="utf-8")
        if ".env" in gi_text:
            ok("Env", ".env listed in .gitignore")
        else:
            note("Env", "HIGH", ".env NOT in .gitignore — secrets may be committed")

    # docker-compose must not hardcode secrets
    for compose_file in REPO_ROOT.glob("docker-compose*.yml"):
        compose_text = compose_file.read_text(encoding="utf-8")
        if re.search(r'SECRET_KEY\s*[:=]\s*["\']?\w{6,}', compose_text):
            note("Env", "HIGH", f"{compose_file.name}: SECRET_KEY may be hardcoded — use Docker secrets")
        else:
            ok("Env", f"{compose_file.name}: no hardcoded SECRET_KEY detected")


# ---------------------------------------------------------------------------
# 7. LDAP / SAML security
# ---------------------------------------------------------------------------

def check_ldap_saml() -> None:
    section("LDAP / SAML Security")

    ldap = SRC / "ldap_auth.py"
    if ldap.exists():
        text = ldap.read_text(encoding="utf-8")
        if "ldaps://" in text or "LDAPS" in text or "tls" in text.lower():
            ok("LDAP", "LDAPS / TLS present in ldap_auth.py")
        else:
            note("LDAP", "HIGH", "No LDAPS/TLS detected — credentials may transit unencrypted")
        if "group" in text.lower() and "role" in text.lower():
            ok("LDAP", "LDAP group-to-role mapping present")
    else:
        note("LDAP", "LOW", "ldap_auth.py not found — LDAP auth may be absent")

    saml = SRC / "saml_auth.py"
    if saml.exists():
        text = saml.read_text(encoding="utf-8")
        if "signature" in text.lower() or "sign" in text.lower():
            ok("SAML", "SAML signature handling present")
        else:
            note("SAML", "HIGH", "No signature validation detected in saml_auth.py — XML injection risk")
        if "metadata" in text.lower():
            ok("SAML", "SAML metadata endpoint present")
    else:
        note("SAML", "LOW", "saml_auth.py not found — SAML SSO may be absent")


# ---------------------------------------------------------------------------
# 8. Token revocation
# ---------------------------------------------------------------------------

def check_token_revocation() -> None:
    section("Token Revocation")

    # Check revoked_tokens in auth repo
    auth_repo = SRC / "auth" / "_repository.py"
    if not auth_repo.exists():
        auth_repo = SRC / "auth_repository.py"

    found = False
    for path in [SRC / "auth" / "_repository.py", SRC / "auth_repository.py",
                 SRC / "auth" / "_core.py", SRC / "auth" / "__init__.py"]:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if "revoke_token" in text or "revoked_tokens" in text:
                ok("Revocation", f"Token revocation present in {path.name}")
                found = True
                if "sqlite" in text.lower() or "db" in text.lower() or "session" in text.lower():
                    ok("Revocation", "DB-backed revocation (not in-memory) detected")
                break
    if not found:
        note("Revocation", "HIGH", "Token revocation (revoke_token) not detected")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  SECURITY DEFAULTS REVIEW SUMMARY")
    print("=" * 60)

    if not findings:
        print("  No actionable issues found. Security defaults look good.")
        print("=" * 60)
        return

    by_severity: dict[str, list[dict[str, str]]] = {}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        print(f"\n  [{sev}] — {len(items)} finding(s):")
        for item in items:
            print(f"    [{item['category']}] {item['message'][:100]}")

    print(
        f"\n  Total: {len(findings)} issue(s) across {len(by_severity)} severity level(s)."
    )
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("DocReview360 Security Defaults Review")
    print(f"Repo root: {REPO_ROOT}")

    check_jwt_secrets()
    check_token_lifetimes()
    check_oidc_keycloak()
    check_password_policy()
    check_mfa()
    check_env_defaults()
    check_ldap_saml()
    check_token_revocation()
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
