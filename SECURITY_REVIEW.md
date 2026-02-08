# SECURITY_REVIEW

## Step 0 - Quick Inventory

| Surface | What I found | Evidence |
|---|---|---|
| App entry points | FastAPI monolith + extra routers, Next.js API routes, Click CLI, Celery tasks | `src/docreview360/api/__init__.py:465`, `src/docreview360/api/approvals.py:29`, `src/docreview360/api/webhooks.py:18`, `frontend/pages/api/tools/checker.ts:14`, `src/docreview360/cli.py:17`, `src/docreview360/approvals.py:53` |
| Data stores | SQLite files for app/auth/roles/search; file/object storage for archive/tamper-proof logs; JSON stores for templates/email templates/settings | `docreview360.db`, `docreview360_users.db`, `docreview360_roles.db`, `search_state.db`, `archive_store/`, `tamper_proof_store/`, `src/docreview360/template_manager.py:18`, `src/docreview360/email_templates.py:22` |
| Upload/download flows | Uploads via `/documents/import`, `/templates`, frontend checker route; downloads via document export/public HTML/template download/archive reports | `src/docreview360/api/__init__.py:1266`, `src/docreview360/api/__init__.py:2147`, `frontend/pages/api/tools/checker.ts:23`, `src/docreview360/api/__init__.py:1385`, `src/docreview360/api/__init__.py:2203`, `src/docreview360/api/__init__.py:1701` |
| Auth/session | JWT bearer auth, cookie auth, RBAC helpers; UI session cookie flow | `src/docreview360/auth.py:842`, `src/docreview360/rbac.py:499`, `src/docreview360/api/__init__.py:2861` |
| External calls | HTTPx/requests to cert endpoints, metabase, sharepoint, webhook subscribers, LLM/network integrations | `src/docreview360/certs.py:67`, `src/docreview360/sharepoint.py:39`, `src/docreview360/api/webhooks.py:47`, `src/docreview360/ai_assist.py:49` |
| Secrets locations | Env-driven secrets (`.env` local), defaults in code, CI secrets use | `src/docreview360/auth.py:86`, `src/docreview360/secrets.py:66`, `.env.example`, `.github/workflows/nightly-tests.yml:255` |

## Step 1 - Threat Model

### Assets
- Documents and revisions
- Approval/signature records
- User accounts, roles, auth tokens/cookies
- API keys/secrets
- Audit logs and tamper-proof chain

### Trust boundaries
- Client -> API (`frontend` and external callers)
- API -> local DB/files/object storage
- API -> external providers (signature/sharepoint/metabase/webhooks)
- CLI/worker -> API/storage/DB

### 10 likely attack paths (priority order)
1. Unauthenticated API CRUD on projects/documents (data exfiltration + tampering).
2. IDOR-like access by guessing IDs on open read/update endpoints.
3. Unauthorized template/email-template manipulation to alter downstream docs/notifications.
4. Token/session abuse via forged or replayed session cookies.
5. Open-redirect phishing from approval callback return URL.
6. SSRF via webhook subscription callbacks to internal services.
7. Upload abuse and public file exposure in frontend checker endpoint.
8. Dependency/supply-chain compromise via runtime `pip install` and unpinned CI actions.
9. XML parser abuse on SAML parser (`fromstring`) in login.gov helper.
10. Infrastructure misconfiguration (weak compose creds, missing IaC hardening/encryption settings).

## Step 2 - Automated Security Scans

### Secret scanning
- Command:
```powershell
rg -n --hidden --glob '!**/.git/**' --glob '!frontend/node_modules/**' --glob '!**/.next/**' --pcre2 "^\s*([A-Za-z0-9_]*(?:SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY|ACCESS_KEY)[A-Za-z0-9_]*)\s*[:=]\s*(.+)$" src frontend docs scripts .github .env .env.example docker-compose.yml requirements.txt pyproject.toml -r '$1=<redacted>'
```
- Key output:
  - hardcoded compose password (`docker-compose.yml:7`)
  - default/static auth secrets in code (`src/docreview360/auth.py:86`, `src/docreview360/auth.py:103`)
  - no direct committed production credentials found in tracked `.env` (only `.env.example` is tracked)
- History scan command:
```powershell
git log --all -p -- .env .env.example | rg -n --pcre2 "^[+-].*(SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY|ACCESS_KEY)"
```
- History result: `no_history_secret_hits`

### Dependency vulnerability audit
- Python command:
```powershell
pip-audit --desc on --verbose
```
- Result: **blocked** by network/proxy restrictions (could not reach `pypi.org`).
- Frontend command:
```powershell
npm audit --omit=dev --prefix frontend --json
```
- Result: `0` prod vulnerabilities.

### SAST / security lint
- Command:
```powershell
bandit -r src/docreview360 -f json -q
```
- Key output summary:
  - total findings: `71` (`63` low, `8` medium)
  - medium findings in:
    - `src/docreview360/login_gov.py:15` (XML parser on untrusted input)
    - `src/docreview360/sharepoint.py:39`, `:50`, `:57`, `:76` (requests without timeout)
    - `src/docreview360/ml/torch_models.py:364`, `:366` (unsafe deserialization)
    - `src/docreview360/certs.py:118` (SHA1 hash usage)
- Semgrep command attempted:
```powershell
semgrep --config p/owasp-top-ten --json --quiet src/docreview360 frontend/pages/api
```
- Result: tooling failed on local cert-store initialization; no Semgrep findings produced.

### Container / IaC / CI scan
- `checkov`/`trivy` unavailable locally.
- Manual IaC/CI checks performed:
  - compose weak static DB password: `docker-compose.yml:7`
  - Terraform resources missing explicit encryption/hardening settings: `iac/rds.tf:12`, `iac/elasticache.tf:12`, `iac/eks.tf:14`
  - GitHub Actions use tag-pinned (not SHA-pinned) actions: `.github/workflows/ci.yml:12`, `.github/workflows/nightly-tests.yml:22`

## Step 3 - Manual Review (A-G)

### A) AuthN/AuthZ
- Major gap: core project/document endpoints remain unauthenticated.
- Fixed in this pass: config/signature-provider endpoints now admin-only; template/email-template endpoints now authenticated/admin-gated.

### B) File upload
- Backend document ingestion validates MIME and size (`documents.py`), but API upload endpoints are still broadly reachable.
- Frontend checker uploads to `/tmp`, then copies files to public web root downloads path.

### C) File download
- Template and email-template downloads were previously unauthenticated; fixed for templates.
- Public document HTML endpoint is intentionally public; route constrained by archive metadata checks.

### D) Input handling / injection
- Open redirect existed in `/approvals/return?next=...`; fixed to local-path-only redirects.
- No direct shell injection found in API handlers; subprocess use is mostly static-arg and/or admin workflow.

### E) Crypto/encryption
- At-rest envelope encryption is AES-GCM and reasonably modern (`crypto.py`).
- Key management relies on env/vault adapter; secure in prod only if env policy is correctly set.
- Risk: permissive dev defaults for auth secrets when env classification is misconfigured.

### F) Logging/telemetry
- Audit/logging coverage exists for major flows.
- No direct secret logging discovered in reviewed API handlers.

### G) Rate limiting & abuse
- ML endpoints have explicit rate limiting.
- No broad rate limiting found for login, document upload/import, or most CRUD APIs.

---

## 1) Executive Summary

Overall posture: **mixed**. The codebase has strong building blocks (RBAC helpers, audit plumbing, crypto primitives), but baseline exposure was weakened by several real-world issues in endpoint protection and web/session hardening.

Highest remaining risks are:
- CI supply-chain hardening (pin actions by SHA + dependency-policy gates)
- GitHub Action SHA pinning is pending verified commit refs

This review implemented immediate high-value hardening patches with minimal diffs and test validation (details below).
Decision point: GitHub Action SHA pinning was not auto-applied in this environment because outbound GitHub lookups are blocked, so exact immutable refs could not be verified safely.

## 2) Findings Table

| Severity | Component | Description | Exploit Scenario | Evidence | Fix Recommendation | Effort |
|---|---|---|---|---|---|---|
| **Critical** | API AuthZ | Core project/document read-write endpoints were unauthenticated. | Remote attacker reads/modifies project/document data without valid token; ID enumeration enables broad exfiltration. | `src/docreview360/api/__init__.py:863`, `src/docreview360/api/__init__.py:995`, `src/docreview360/api/__init__.py:1366`, `src/docreview360/api/__init__.py:1460`, `src/docreview360/api/__init__.py:1532`, `src/docreview360/api/__init__.py:1794` | **Fixed**: enforced bearer auth + object-level authorization checks on core project/document/cms/archive/search/watchlist APIs; public copy routes remain explicitly public. | M-L |
| **High** | API AuthZ (Templates) | Template/email-template endpoints were unauthenticated for read/write. | Attacker can alter templates used for policy docs/email notifications, enabling content tampering and phishing workflows. | `src/docreview360/api/__init__.py:2127`, `src/docreview360/api/__init__.py:2144`, `src/docreview360/api/__init__.py:2264` (pre-fix behavior) | **Fixed**: require authenticated/admin roles on these endpoints. | S |
| **High** | Session/Auth | UI session cookie previously trusted raw username, allowing cookie forgery risk. | Attacker sets `session=<victim>` cookie to access UI views as another user. | `src/docreview360/api/__init__.py:2861`, `src/docreview360/api/__init__.py:2870` (pre-fix) | **Fixed**: signed + age-checked session cookie via HMAC. | S |
| **High** | Redirect handling | Open redirect in approval return flow accepted arbitrary `next` URL. | Phishing chain from trusted domain: victim signs and is redirected to attacker host. | `src/docreview360/api/approvals.py:75` (pre-fix) | **Fixed**: only local relative paths accepted. | S |
| **High** | CORS | Previous default allowed credentials for any origin via regex `.*`. | Malicious site can read credentialed API responses in browser context. | `src/docreview360/api/__init__.py` CORS fallback block (pre-fix) | **Fixed**: explicit localhost-only defaults unless allowlist env is set. | S |
| **High** | Abuse controls | Auth and upload endpoints lacked request throttling. | Credential stuffing or upload flooding can cause account lockouts and service degradation. | `src/docreview360/api/__init__.py:3232`, `src/docreview360/api/__init__.py:3294`, `src/docreview360/api/__init__.py:1516` (pre-fix behavior) | **Fixed**: added fixed-window rate limiting on `/token`, `/login`, and `/documents/import` with env-tunable limits. | S |
| **Medium** | Admin config integrity | Config and signature-provider endpoints were accessible without admin auth. | Attacker changes auth/cms/provider behavior to weaken controls or disrupt signature verification flow. | `src/docreview360/api/__init__.py:3325`, `src/docreview360/api/__init__.py:3348` (pre-fix) | **Fixed**: `require_role("admin")` on get/update endpoints. | S |
| **Medium** | SAML parsing | Login.gov parser used unsafe stdlib XML parsing for untrusted SAML. | Crafted XML payload can trigger parser abuse/DoS classes. | `src/docreview360/login_gov.py:13` (pre-fix behavior) | **Fixed**: switched to `defusedxml`, strict base64 decode, payload size limit, and DTD/entity rejection. | S |
| **Medium** | External HTTP resilience | SharePoint requests lacked explicit timeout handling. | Slow upstream can hang worker threads and exhaust resources (availability impact). | `src/docreview360/sharepoint.py:55`, `src/docreview360/sharepoint.py:71`, `src/docreview360/sharepoint.py:82`, `src/docreview360/sharepoint.py:105` (pre-fix behavior) | **Fixed**: added centralized request timeout on all Graph calls. | S |
| **Medium** | Upload/download surface | Frontend checker route wrote user files under web-accessible `public/downloads`. | Uploaded content became directly reachable by URL and retained on disk. | `frontend/pages/api/tools/checker.ts:54`, `:57` (pre-fix) | **Fixed**: move files to private `.tmp` storage with expiring one-time token downloads and extension/size checks. | M |
| **Medium** | Secrets/config defaults | Dev-secret defaults and permissive demo seeding increased blast radius if env was mis-set. | Deployment with missing env vars could run with weak/predictable signing posture and demo-user behavior. | `src/docreview360/auth.py:91`, `src/docreview360/auth.py:137`, `src/docreview360/auth.py:153`, `src/docreview360/auth.py:443` | **Fixed**: generated high-entropy dev fallback secrets, enforced strong secrets outside local/test, disabled default demo seeding, and blocked production demo seeding even when flag is set. | M |
| **Medium** | IaC/compose hardening | Compose/TF templates lacked hardening controls. | Weak local defaults can be promoted into staging/prod. | `docker-compose.yml:7`, `docker-compose.yml:9`, `iac/rds.tf:17`, `iac/eks.tf:17`, `iac/elasticache.tf:16` | **Fixed**: required external DB password + SCRAM init, enabled RDS encryption/backup/deletion protection, made EKS endpoint private with audit logs, and moved Redis to encrypted replication-group configuration with auth token support. Remaining: CI action SHA pinning. | M |
| **Low** | Dependency scanning coverage | Python dependency audit blocked by network/proxy limits. | Vulnerable transitive packages may go undetected locally. | `pip-audit` command failure (proxy connection refused) | Run `pip-audit` in CI with network access and fail-on-high policy. | S |

## 3) Fix-First Plan (First 5 Patches)

1. Enforce auth-by-default for project/document APIs with explicit public allowlist (**decision point for compatibility**).
2. Add rate limiting + abuse controls on `/token`, `/login`, `/documents/import`.
3. Harden frontend checker upload/download path (private storage + auth-checked fetch).
4. Replace unsafe XML parser in `login_gov.py` with `defusedxml`.
5. Add timeout+retry policy to SharePoint client and pin CI action SHAs.

## 4) Post-Fix Verification Checklist

- Re-run unit tests for hardened endpoints and auth flows:
  - `pytest -q tests/test_login.py tests/test_config_endpoints.py tests/test_approval_api.py tests/test_template_api_flow.py tests/test_template_approval_flow.py`
- Re-run SAST:
  - `bandit -r src/docreview360 -f json -q`
- Re-run dependency audits with network-enabled CI:
  - `pip-audit --desc on --strict`
  - `npm audit --omit=dev --prefix frontend --json`
- Re-run secret scan in CI (tracked files + history).
- Add integration tests asserting 401/403 on non-public endpoints without auth.

## Step 5 - Implemented Fixes in This Pass

Implemented directly in code (minimal diffs):
- Open redirect blocked in approval return flow.
  - `src/docreview360/api/approvals.py:38`, `src/docreview360/api/approvals.py:97`
- Signed, expiring session cookie handling for UI routes.
  - `src/docreview360/api/__init__.py:645`, `src/docreview360/api/__init__.py:658`, `src/docreview360/api/__init__.py:2861`, `src/docreview360/api/__init__.py:2870`, `src/docreview360/api/__init__.py:2894`
- Secure CORS default (no wildcard+credentials fallback).
  - `src/docreview360/api/__init__.py:502`
- Admin-only access for config and signature-provider endpoints.
  - `src/docreview360/api/__init__.py:3325`, `src/docreview360/api/__init__.py:3334`, `src/docreview360/api/__init__.py:3348`, `src/docreview360/api/__init__.py:3360`
- Auth/admin protection added for template + email-template APIs.
  - `src/docreview360/api/__init__.py:2127`, `src/docreview360/api/__init__.py:2147`, `src/docreview360/api/__init__.py:2264`, `src/docreview360/api/__init__.py:2295`
- Enforced authenticated, object-level authorization for core data APIs.
  - `src/docreview360/api/__init__.py:863`, `src/docreview360/api/__init__.py:899`, `src/docreview360/api/__init__.py:995`, `src/docreview360/api/__init__.py:1217`, `src/docreview360/api/__init__.py:1366`, `src/docreview360/api/__init__.py:1532`, `src/docreview360/api/__init__.py:1655`, `src/docreview360/api/__init__.py:1794`, `src/docreview360/api/__init__.py:2012`, `src/docreview360/api/__init__.py:2085`
- Hardened audit-log authorization to use authenticated identity (no trusted spoofable header).
  - `src/docreview360/api/__init__.py:557`
- Added endpoint abuse controls for auth and file upload flows.
  - `src/docreview360/api/__init__.py:215`, `src/docreview360/api/__init__.py:258`, `src/docreview360/api/__init__.py:1516`, `src/docreview360/api/__init__.py:3232`, `src/docreview360/api/__init__.py:3294`
- Replaced unsafe SAML XML parsing with `defusedxml` plus input hardening.
  - `src/docreview360/login_gov.py:6`, `src/docreview360/login_gov.py:9`, `src/docreview360/login_gov.py:13`
- Added SharePoint HTTP timeouts on all Graph API calls.
  - `src/docreview360/sharepoint.py:41`, `src/docreview360/sharepoint.py:62`, `src/docreview360/sharepoint.py:77`, `src/docreview360/sharepoint.py:88`, `src/docreview360/sharepoint.py:112`
- Removed public-webroot checker artifacts; added private expiring token downloads.
  - `frontend/pages/api/tools/checker.ts:16`, `frontend/pages/api/tools/checker.ts:50`, `frontend/pages/api/tools/checker.ts:129`
  - `frontend/pages/tools/checker.tsx:24`, `frontend/pages/tools/checker.tsx:56`
- Hardened auth secret and demo-user safety defaults.
  - `src/docreview360/auth.py:35`, `src/docreview360/auth.py:44`, `src/docreview360/auth.py:91`, `src/docreview360/auth.py:137`, `src/docreview360/auth.py:153`, `src/docreview360/auth.py:443`
- Hardened local/infra templates with safer defaults.
  - `docker-compose.yml:7`, `docker-compose.yml:9`, `iac/rds.tf:17`, `iac/eks.tf:17`, `iac/elasticache.tf:16`
- Removed exception-swallowing cache fallbacks in API read paths.
  - `src/docreview360/api/__init__.py:972`, `src/docreview360/api/__init__.py:1561`, `src/docreview360/api/__init__.py:1637`, `src/docreview360/api/__init__.py:2129`
- Tests updated/added for new controls.
  - `tests/test_approval_api.py`, `tests/test_login.py`, `tests/test_config_endpoints.py`, `tests/test_template_api_flow.py`, `tests/test_template_approval_flow.py`, `tests/test_project_reviewers_api.py`, `tests/test_project_document_authz.py`, `tests/test_rate_limiting_security.py`, `tests/test_login_gov.py`, `tests/test_sharepoint.py`, `tests/auth/test_secrets.py`, `tests/test_token_env.py`, `tests/auth/test_password_policy.py`

Validation completed:
- `ruff check src/docreview360/api/__init__.py src/docreview360/login_gov.py src/docreview360/sharepoint.py tests/test_rate_limiting_security.py tests/test_login_gov.py tests/test_sharepoint.py tests/test_approval_cms.py tests/unit/test_sharepoint_upload_and_versions.py`
- `ruff check src/docreview360/auth.py tests/auth/test_secrets.py tests/test_token_env.py tests/auth/test_password_policy.py`
- `ruff check src/docreview360/api/__init__.py src/docreview360/auth.py tests/auth/test_secrets.py tests/test_token_env.py tests/auth/test_password_policy.py`
- `bandit -r src/docreview360/api/__init__.py src/docreview360/auth.py src/docreview360/login_gov.py src/docreview360/sharepoint.py -f json -q`
- `pytest -q tests/test_rate_limiting_security.py tests/test_login_gov.py tests/test_sharepoint.py tests/test_approval_cms.py tests/unit/test_sharepoint_upload_and_versions.py tests/test_project_document_authz.py tests/test_project_reviewers_api.py tests/test_login.py tests/test_config_endpoints.py tests/test_approval_api.py tests/test_template_api_flow.py tests/test_template_approval_flow.py -o cache_dir=.tmp/pytest-cache`
- `pytest -q tests/auth/test_secrets.py tests/test_token_env.py tests/auth/test_password_policy.py tests/auth/test_auth.py tests/auth/test_login_mfa.py -o cache_dir=.tmp/pytest-cache`
- `pytest -q tests/test_rate_limiting_security.py tests/test_login_gov.py tests/test_sharepoint.py tests/test_approval_cms.py tests/unit/test_sharepoint_upload_and_versions.py tests/test_project_document_authz.py tests/test_project_reviewers_api.py tests/test_login.py tests/test_config_endpoints.py tests/test_approval_api.py tests/test_template_api_flow.py tests/test_template_approval_flow.py tests/auth/test_secrets.py tests/test_token_env.py tests/auth/test_password_policy.py tests/auth/test_auth.py tests/auth/test_login_mfa.py -o cache_dir=.tmp/pytest-cache`
- Result: **32 passed** + **18 passed** + **50 passed** targeted suites; Bandit now reports **0 findings** in `api/__init__.py`, `login_gov.py`, and `sharepoint.py` and only low-severity heuristic hits in `auth.py`.
