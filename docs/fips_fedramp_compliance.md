# FIPS 140-2 and FedRAMP Compliance Guide

## FIPS 140-2 Validated Cryptography Usage

DocReview360 uses the following cryptographic primitives. Each is FIPS 140-2 compatible when
the underlying Python runtime is linked against a FIPS-validated OpenSSL module.

| Component | Algorithm | FIPS Status | Location |
|-----------|-----------|-------------|----------|
| JWT access tokens | HMAC-SHA256 (HS256) | ✅ FIPS-compliant | `auth.py`, env `DOCREVIEW360_ALGORITHM` |
| Password hashing | bcrypt | ⚠️ Use PBKDF2 in strict FIPS mode | `auth.py` — see note below |
| Column encryption | AES-256-GCM | ✅ FIPS-compliant | `db_encryption.py` |
| TLS transport | TLS 1.2 / TLS 1.3 | ✅ FIPS-compliant ciphers available | `nginx/nginx.conf` |
| Audit log chaining | SHA-256 | ✅ FIPS-compliant | `logs/_dispatch.py`, `logs/_query.py` |
| HMAC webhook signing | HMAC-SHA256 | ✅ FIPS-compliant | `api/webhooks.py` |
| OIDC/PKCE code verifier | SHA-256 | ✅ FIPS-compliant | `oidc_client.py` |
| eDiscovery backup | AES-256-CBC (openssl) | ✅ FIPS-compliant | `scripts/db_backup.sh` |

### Running in FIPS Mode

To enable FIPS mode, set:

```bash
export DOCREVIEW360_FIPS_MODE=true
```

When `DOCREVIEW360_FIPS_MODE=true` is set:
- The application will log a warning if bcrypt is detected as the password hasher.
- PBKDF2-HMAC-SHA256 is the recommended alternative password hasher for strict FIPS environments.
- Ensure the Python interpreter is built against a FIPS-validated OpenSSL module (e.g., OpenSSL 3.x with FIPS provider).

### bcrypt Note

bcrypt is not FIPS 140-2 validated. For federal deployments requiring strict FIPS compliance:

1. Configure your identity provider (LDAP/AD, SAML, OIDC) to handle authentication externally.
2. Or switch the internal password hasher to PBKDF2:
   ```bash
   export DOCREVIEW360_PASSWORD_HASHER=pbkdf2_sha256
   ```
   (Requires `DOCREVIEW360_ENV` ≠ `production` to override the default.)

---

## FedRAMP Control Mapping

The following table maps key NIST SP 800-53 Rev. 5 controls to DocReview360 capabilities.
This mapping is informational and supports a FedRAMP authorization package (3PAO assessment required).

| Control ID | Control Name | DocReview360 Implementation |
|------------|--------------|---------------------------|
| **AC-2** | Account Management | User CRUD via `/users/*` and `/scim/v2/Users`; org-scoped access; SCIM lifecycle management |
| **AC-3** | Access Enforcement | RBAC via `require_permission()` and `require_role()`; org_id isolation on all project queries |
| **AC-6** | Least Privilege | Role-based permission matrix at `GET /rbac/matrix`; default minimal permissions per role |
| **AC-7** | Unsuccessful Login Attempts | Configurable lockout via `DOCREVIEW360_MAX_FAILED_ATTEMPTS` and `DOCREVIEW360_LOCKOUT_SECONDS` |
| **AC-11** | Session Lock | Idle session timeout via `OIDC_IDLE_TIMEOUT_MINUTES`; absolute session lifetime |
| **AC-12** | Session Termination | Server-side session revocation at `DELETE /sessions/{id}`; JWT revocation table |
| **AU-2** | Event Logging | Comprehensive audit log via `logs/` package; 50+ action types logged |
| **AU-3** | Content of Audit Records | Each entry captures: timestamp, user_id, action, entity_type, entity_id, IP, details |
| **AU-9** | Protection of Audit Information | SHA-256 hash chain; SQLite `BEFORE UPDATE/DELETE` triggers; `verify_audit_log_chain()` |
| **AU-11** | Audit Record Retention | Configurable via `DOCREVIEW360_RETAIN_AUDIT_LOGS_DAYS`; data retention module |
| **IA-2** | Identification and Authentication | JWT HS256 + bcrypt/PBKDF2; TOTP MFA; PIV/CAC smart card; FIDO2/WebAuthn |
| **IA-5** | Authenticator Management | Password history enforcement; max age; complexity policy; SCIM credential lifecycle |
| **IA-8** | Non-Organizational User ID | OIDC Authorization Code + PKCE; SAML 2.0 SP; LDAP/AD with LDAPS |
| **SC-8** | Transmission Confidentiality | TLS 1.2/1.3 enforced at nginx; HSTS header; HTTP → HTTPS redirect |
| **SC-12** | Cryptographic Key Establishment | HMAC-SHA256 keys from environment; column encryption key via `DOCREVIEW360_COLUMN_ENCRYPTION_KEY` |
| **SC-28** | Protection of Information at Rest | AES-256-GCM column encryption (`db_encryption.py`); encrypted backup (`scripts/db_backup.sh`) |
| **SI-7** | Software, Firmware, and Information Integrity | Docker image hash verification; pip-audit in CI; pre-commit security hooks |
| **SI-12** | Information Management | NARA records management metadata; data retention policies; legal hold |
| **MP-6** | Media Sanitization | Configurable data retention purge; legal hold prevents premature deletion |
| **PS-4** | Personnel Termination | SCIM `DELETE /scim/v2/Users/{id}`; account deactivation; session revocation on logout |
| **SA-11** | Developer Testing and Evaluation | 90% branch coverage gate; bandit SAST; ruff linting; pre-commit hooks |

---

## Section 508 / WCAG 2.1 AA

See [section508_wcag.md](section508_wcag.md) for the accessibility compliance guide.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCREVIEW360_FIPS_MODE` | `false` | Enable FIPS mode warnings and enforcements |
| `DOCREVIEW360_PASSWORD_HASHER` | `bcrypt` | Password hasher: `bcrypt` or `pbkdf2_sha256` |
| `DOCREVIEW360_COLUMN_ENCRYPTION_KEY` | — | 64-hex-char AES-256 key for field encryption |
| `DOCREVIEW360_RETAIN_AUDIT_LOGS_DAYS` | — | Days to retain audit logs (unset = forever) |
