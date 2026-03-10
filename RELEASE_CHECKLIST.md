# DocReview360 Release Checklist (Open Items Only)

This file tracks unfinished work only.

Completed work moved to:

- `docs/latest_features.md`
- `docs/release-completed-items.md`

Target window: next month (confirm exact date and time zone).

## Release blockers and execution

### Auth and security gaps

- [ ] Full Keycloak integration (JWKS validation, claim-to-role mapping).

### 13) Scope and release targets

- [x] Decide release artifacts: GitHub release, PyPI package, and Docker image are in scope for v0.1. A separate docs site is not required for v0.1; docs ship in-repo via `README.md` and `docs/`.
- [x] Decide support scope: full stack. Release and verification must cover API, frontend, workers, packaging, and deployment surfaces. This is not a CLI-only release.
- [ ] Define supported platforms and document them.
- [ ] Freeze feature scope. Fixes only after this checkpoint.
- [ ] Create a release branch and protect `main`.

### 14) Repository hygiene and public readiness

- [ ] Run a secret scan on the full history and working tree.
- [ ] Remove or rotate any hardcoded tokens, test credentials, or sample secrets.
- [ ] Remove unnecessary files and stale artifacts before release.
- [ ] Ensure all `example.com` and placeholder URLs or emails are updated.
- [ ] Confirm the `SECURITY.md` contact email is real and monitored.

### 15) Packaging and versioning

- [ ] Decide and document the versioning scheme in `CHANGELOG.md`.
- [ ] Test install from the built artifacts in a clean environment.
- [ ] If publishing, perform a TestPyPI dry run.
- [ ] Decide whether frontend assets are part of the PyPI package and document the answer.

### 15a) Publish payload and exclusion rules

**PyPI wheel and sdist must include only release artifacts**

- [ ] Ship only runtime Python package contents needed by installs:
  `src/docreview360/**`, required templates, migrations, runtime JSON or schema files,
  `README.md`, `LICENSE`, and package metadata.
- [ ] Exclude `tests/` from the published sdist. The current `dist/docreview360-0.1.2.tar.gz`
  still includes the full test tree.
- [ ] Review `[tool.setuptools.package-data]` and replace the broad wildcard rule with an
  explicit allowlist of runtime assets.
- [ ] Verify the wheel does not ship runtime-generated state or logs.
- [ ] Regenerate the wheel and sdist and inspect the file lists before publish.

**Docker image and build context must exclude local junk**

- [x] Add a `.dockerignore`.
- [x] Exclude at least: `.git/`, `.github/`, `docs/`, `tests/`, `dist/`, `build/`,
  `.venv/`, `frontend/node_modules/`, `.coverage*`, `.pytest_cache/`, `.mypy_cache/`,
  `.ruff_cache/`, `.hypothesis/`, `.e2e-debug/`, `.e2e-debug-webpack/`, `.pytest_tmp/`,
  `.tmp/`, local DB files, and local JSON state files.
- [ ] Stop the Docker build from copying unnecessary repo content after dependency install,
  or verify `.dockerignore` fully protects the build context.
- [x] Update the Docker OCI license label from `GPL-3.0-only` to `MIT`.
  (Dockerfile `org.opencontainers.image.licenses` updated to `MIT`.)

**Repository ignore list should be tightened before public release**

- [x] Add ignore rules for current local-only artifacts:
  `.e2e-debug/`, `.e2e-debug-webpack/`, `.pytest_tmp/`, `worker_state.json`,
  `workflow_templates.json`, `workflow_templates.json.lock`, `email_templates.json`,
  `email_templates.json.lock`, `template_store.json`, `template_store.json.lock`,
  `docreview360.db`, `docreview360_roles.db`, `docreview360_users.db`, `search_state.db`,
  and `frontend/workflow_templates.json`.
- [x] Decide whether `frontend/document_types.json`, `frontend/phases.json`, and
  `frontend/phase_workflow_links.json` are still needed. Remove or ignore them if not.
  (Added to .gitignore as legacy files superseded by the database.)
- [x] Remove or ignore `frontend/pages__backup_js_*` before release. (Added to .gitignore.)

**Public GitHub repository readiness**

- [ ] Remove local or internal-only root files before making the repo public, or move them
  out of the default branch: `_debug_test.py`, `ai-notes.md`, `push-after-fix.ps1`,
  `tatus`, local DB files, and ad hoc runtime JSON stores.
- [ ] Review `.dev/`, `.claude/`, `CLAUDE.md`, and `CLAUDE_CODE_UPDATES.md` and decide
  whether they belong in the public repository.
- [ ] Replace public-facing placeholders and stale metadata:
  `info@example.com`, `example.com` URLs, `registry.example.com`, and stale GPL references.
- [ ] Update docs and metadata that still mention GPL or placeholder contact data.
- [ ] Review references to private repositories and remove or clearly mark them as optional.
- [ ] Confirm branch protection, issue tracker settings, security reporting, and Actions
  settings are ready for a public repository.

### 16) Documentation and user experience

- [ ] Audit docs in `docs/` for broken links and outdated instructions.
- [ ] Ensure `README.md` matches `.dev/AGENTS.md` structure requirements.
- [ ] Add or verify a Quick Start that works on Windows and macOS/Linux.
- [ ] Publish `docs/adr/0001-core-architecture.md` and verify accuracy.
- [ ] Generate FastAPI API docs and link them from the README.
- [ ] If using MkDocs, run `mkdocs build --strict` and fix errors.

### 17) Backend quality gates

- [ ] Run `pytest -q`.
- [ ] Run `pytest -q --cov=src --cov-branch --cov-report=term --cov-fail-under=90`.
- [ ] Run `mypy --strict src tests` if type coverage is ready.
- [ ] Run `mutmut run`.
- [ ] Run `trivy fs .`.

### 18) Frontend-backend integration

- [ ] Run E2E smoke.
- [ ] Run E2E full.
- [ ] Manually verify the full flow on a clean environment.
- [ ] Verify login works as admin (`alice`) and non-admin (`bob`).
- [ ] Verify project creation persists after refresh.
- [ ] Verify document upload, view, and edit from the UI.
- [ ] Verify approval request flow updates status in the UI.
- [ ] Verify PDF and Markdown export from UI or CLI.
- [ ] Verify `NEXT_PUBLIC_API_BASE` against the deployed backend URL.
- [ ] Verify CORS allows the frontend origin.
- [ ] Verify UI error handling when the backend is unavailable.

### 19) CI/CD and automation

- [ ] Verify GitHub Actions CI passes on a clean run.
- [ ] Ensure the CI coverage threshold matches the release gate.
- [ ] Decide whether to automate PyPI publish on tag.

### 20) Security and compliance

- [ ] Review `SECURITY_REVIEW.md` and close or document open items.
- [ ] Validate that security checks mentioned in `SECURITY.md` actually run.
- [ ] Confirm password policy, secrets management, and encryption-at-rest docs are accurate.
- [ ] Verify OAuth/OIDC defaults and token lifetimes are reasonable for public use.
- [ ] Ensure audit log integrity checks are enabled and documented.

### 21) Infrastructure and deployment readiness

- [ ] Verify Docker build works end to end.
- [ ] Validate `docker-compose.yml` brings up all dependencies.
- [ ] Confirm `docs/deployment.md` matches current env vars and services.
- [ ] Validate `settings.yaml` defaults are safe for production.

### 22) Code review and fix-it loop

- [ ] Run targeted code review for backend.
- [ ] Run targeted code review for frontend.
- [ ] Run targeted code review for CLI and scripts.
- [ ] Document prompt intent and expected behavior before optimization changes.
- [ ] For each optimization change, run targeted tests first, then rerun unit and impacted E2E tests.
- [ ] For each review, open issues, fix them, and rerun the relevant tests.
- [ ] Ensure risky changes are covered by tests.

### 23) Release execution

- [ ] Bump version in `pyproject.toml` and align frontend versioning if needed.
- [ ] Update `CHANGELOG.md` with release notes and date.
- [ ] Tag the release in git.
- [ ] Create the GitHub release with notes, assets, and checksums.
- [ ] Publish to PyPI after TestPyPI verification, if chosen.
- [ ] Publish the Docker image, if chosen, and verify tags.
- [ ] Announce the release with upgrade notes and known issues.

### 24) Post-release verification

- [ ] Install from PyPI into a fresh venv and run `docreview360 --help`.
- [ ] Smoke test the CLI to API to UI flow using released artifacts.
- [ ] Verify docs site or README links resolve correctly.
- [ ] Monitor issues and security reports for the first week.

### 43) 2026-03-10 review addendum

**43a) Token revocation is still process-local**

- [x] Move token revocation to a DB table or Redis-backed store.
  (Implemented: `revoked_tokens` SQLite table in the auth DB via `UserRepository.revoke_token()` / `.is_token_revoked()`.)

**43b) Workflow template persistence is still file-backed**

- [x] Remove disk fallback for workflow templates.
  (DB-only persistence via `workflow_template_records`; disk load/save functions removed.)
- [x] Remove the workflow template file-based env var from the runtime path.
  (`WORKFLOW_TEMPLATES_FILE` and file-based path removed; `DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE` retained to toggle DB persistence.)

**43c) Duplicate API registration remains**

- [ ] Keep the router-based implementation or the legacy monolith, but not both.

**43d) Frontend API migration is incomplete**

- [x] Replace remaining protected-page raw `fetch(...)` calls with `authenticatedFetch(...)`.
  (All 38 raw fetch calls in pages/ migrated; login.tsx intentionally kept as raw fetch.)
- [ ] Broaden the frontend raw-fetch guard so it catches `fetch(`${API}/...`)`.
  (Remaining: pages with `authenticatedFetch(\`${API}/...\`)` work correctly but could use relative paths.)

**43e) `filelock` cleanup is not complete**

- [x] Remove remaining `filelock` runtime usage.
  (All three modules migrated to SQLite: `email_templates.py` → `email_template_records` table;
  `template_manager.py` → `golden_template_records` table; `workflows.py` → disk fallback fully removed.
  `filelock` dependency removed from `pyproject.toml`.)

**43f) Plugin marketplace frontend/backend contract mismatch**

- [x] Add the missing plugin marketplace routes or remove the frontend calls.
  (Added `GET /plugin-marketplace/builtin-status` and `POST /plugin-marketplace/toggle` to `admin_router.py`;
  added `get_builtin_status()` and `set_builtin_plugin_state()` to `plugin_marketplace.py`.)

## Product and architecture backlog

### Document version lineage

- [ ] Branch and merge support for parallel review tracks.

### 30) Large modules needing decomposition

- [x] Decompose remaining large modules: `logs.py` → `logs/` package (`_db.py`, `_dispatch.py`, `_query.py`, `__init__.py`); `reporting.py` → `reporting/` package (`_models.py`, `_metrics.py`, `_reports.py`, `__init__.py`). All public APIs preserved via `__init__.py` re-exports.
- [ ] Decompose remaining large modules: `auth.py`, `search.py`, `workflows.py`, `doc_types.py`, `documents.py` (lower priority, defer to post-v0.2).

### 31) Frontend state management

- [x] Introduce centralized server-state handling: React Query (`@tanstack/react-query`) configured in `_app.tsx` with global `staleTime`, `gcTime`, retry, and `refetchOnWindowFocus` defaults.
- [x] New hooks in `frontend/lib/`: `useProjects.ts`, `useDocuments.ts`, `useNotifications.ts`, `useSessions.ts` — all using `authenticatedFetch`, optimistic updates, and shared cache keys.
- [ ] Migrate remaining pages from inline `fetch()` to the new hooks (ongoing integration work).

### 32) YAML configuration loaders

- [x] Consolidated: new `yaml_loader.py` with `load_yaml_file()`, `save_yaml_file()`, `YamlConfigLoader` base class. All six target modules (`config.py`, `environment.py`, `provider_store.py`, `rbac_editor.py`, `schedule_editor.py`, `settings_manager.py`) updated to use the shared loader. Atomic writes via `tempfile.mkstemp` + `os.replace`.

### 34) Federal Style Validator integration

**Architecture decision (2026-03-10):** Federal Style Validator (FSV) is a separate,
dedicated application that will be published as its own MIT-licensed package on PyPI
(and other registries). DocReview360 is an integration host — it must not duplicate
FSV's style, readability, quality, or regulatory logic internally.

**Integration contract:**

```
FSV (separate MIT package on PyPI, authoritative for all style/quality work)
  └── exposes: /validate, /quality, /readability, /regulatory-check (TBD by FSV)

DocReview360 backend
  └── thin proxy endpoints that forward to FSV and cache results in DB
  └── config: FEDERAL_STYLE_VALIDATOR_URL (base URL of running FSV instance)

DocReview360 editor integrations
  └── TipTap: FSV-provided TipTap plugin/extension (client to FSV's API)
  └── Other authoring tools: FSV-provided plugins (future)
```

**Internal implementations to remove once FSV integration is complete:**

- `tiptapFederalStyleLint.ts` — local regex/rule validation; replace with FSV's TipTap plugin
- `regulatory.py` — pattern-matching reimplementation; replace with proxy to FSV
- `ml/onnx_infer.py` quality scoring — replace with FSV quality output (keep model infra if FSV uses it)
- Inline preflight style checks in `checker.tsx` — replace with FSV API calls
- Local readability/plain-language scoring — FSV is authoritative for this

**What DocReview360 keeps:**

- Integration layer (proxy endpoints calling FSV, returning results to the UI)
- Result persistence (cache FSV scores in DB for history, sparklines, KPI cards)
- UI rendering of FSV output (decorations in TipTap, result cards, quality score table)
- Access control (authenticated users only for FSV calls)

**Phase 1 — Integration layer (prerequisite: FSV API contract defined)**

- [ ] Add `FEDERAL_STYLE_VALIDATOR_URL` config setting and document it.
- [ ] Replace `POST /documents/preflight` style checks with proxy call to FSV.
- [ ] Replace `POST /ai/regulatory-check` with proxy call to FSV regulatory endpoint.
- [ ] Replace `POST /ml/quality` scoring with proxy call to FSV quality endpoint.
- [ ] Remove `regulatory.py` duplicate pattern matching once FSV proxy is live.

**Phase 2 — Editor integration (prerequisite: FSV TipTap plugin exists)**

- [ ] Register FSV's TipTap plugin in `frontend/extensions/registry.ts`.
- [ ] Remove `tiptapFederalStyleLint.ts` (local reimplementation) once FSV plugin is wired in.
- [ ] Add sidebar panel showing live FSV validation summary and overall score.
- [ ] Configure FSV endpoint URL in the editor plugin via DocReview360's settings API.

**Phase 3 — Full cutover and documentation**

- [ ] Confirm no remaining duplicate style/quality logic in DocReview360 source.
- [ ] Document integration points, config, and FSV version requirements in `docs/federal-style-validator.md`.
- [ ] Add FSV as an optional dependency in `pyproject.toml` with install instructions.
- [ ] Define FSV version pinning and compatibility policy.

### 35) AI quality scores in project view

**Note:** Once FSV integration (item 34) is complete, quality scores must come from FSV,
not from internal scoring. The persistence and UI work below remains valid regardless of
the score source.

- [ ] Add `last_quality_score`, `last_quality_date`, and `plain_language_grade` persistence.
- [ ] Compute and store scores on document changes or preflight runs (via FSV proxy once available).
- [ ] Add score history sparkline or trend indicator per document.
- [ ] Include quality score summary in dashboard KPI cards.

### 36) License migration follow-up

- [x] Audit transitive dependencies for GPL contamination. Findings: `psycopg` (LGPLv3) is optional `[postgres]` extra; `pyphen`/`cmudict` are transitive via `textstat` (data resources, dynamically linked); `semgrep` is dev-only; `govdocverify`/FedStyleValidator (GPL-3.0, same author) is optional `[fedstylevalidator]` extra. No mandatory GPL runtime dependencies.
- [x] Add `SPDX-License-Identifier: MIT` headers to all 182 Python source files in `src/docreview360/`.
- [x] Generated `docs/licenses-report.md` with full dependency license table and notes on non-MIT packages.
- [x] Verified no vendored third-party code with incompatible licenses in `src/`.

### 37) Authentication and identity provider integration

**Phase 1 — Core SSO and directory**

- [x] Full OIDC and OAuth 2.0 provider integration with Authorization Code + PKCE.
  (New `oidc_client.py`: PKCE pair generation, provider discovery, state/nonce DB storage, code exchange, ID token validation.
  New routes: `GET /oidc/authorize`, `GET /oidc/callback` with JIT user provisioning + DocReview360 JWT issuance.)
- [x] LDAP and Active Directory integration with LDAPS and group-to-role mapping.
  (`ldap_auth.py`: `authenticate_ldap()` with service-account search + user-bind; `get_ldap_groups()` with RFC 4515 escaping; `map_ldap_groups_to_roles()` from `LDAP_ROLE_MAP` JSON; `ldap_login()` integrated into `auth.py` `login_for_access_token` as fallback after local auth. All `ldap3` imports guarded with `try/except ImportError`.)
- [x] SAML 2.0 SP support.
  (`saml_auth.py`: `build_auth_request()`, `process_saml_response()`, `get_sp_metadata()`; `api/saml_router.py`: `GET /saml/login`, `POST /saml/acs` with JIT provisioning + JWT issuance, `GET /saml/metadata`, `POST /saml/sls`. Router registered in `api/__init__.py`. All `python3-saml` imports guarded.)
- [x] Session management hardening: idle timeout, absolute lifetime, concurrent session limits, server-side revocation.
  (`UserSessionRecord` SQLAlchemy model; `create_user_session()` enforces concurrent session limit (configurable via `OIDC_SESSION_MAX_CONCURRENT`);
  `touch_session()` enforces idle timeout (`OIDC_IDLE_TIMEOUT_MINUTES`); revocation on logout via `revoke_user_session()`;
  `GET /sessions`, `DELETE /sessions/{session_id}` endpoints for user self-service.)

**Phase 2 — Federal and DoD authentication**

- [x] CAC/PIV smart card authentication.
  (`src/docreview360/piv_cac.py`: `piv_enabled()`, `extract_piv_identity()` — extracts EDIPI, email, UPN, org from X.509 cert SAN/subject; `_check_revocation()` via OCSP (fails open); `authenticate_piv()` returns (username, roles); `extract_cert_from_headers()` for nginx `X-Client-Cert` proxy header. `POST /piv/verify` in `auth_router.py` JIT-provisions and issues JWT.)
- [x] FIDO2 and WebAuthn support.
  (`src/docreview360/webauthn_auth.py`: optional `py-webauthn>=2.0` dep; SQLite credential store in `.webauthn.db`; `begin_registration()`/`complete_registration()`, `begin_authentication()`/`complete_authentication()`, `list_credentials()`, `delete_credential()`. Six endpoints in `auth_router.py`: `POST /webauthn/register/begin`, `POST /webauthn/register/complete`, `POST /webauthn/authenticate/begin`, `POST /webauthn/authenticate/complete`, `GET /webauthn/credentials`, `DELETE /webauthn/credentials/{credential_id}`.)
- [x] Password policy enforcement with history, expiry, and lockout controls.
  (`src/docreview360/auth.py`: `password_history` table and `password_changed_at` column auto-migrated; `PasswordPolicy.history_count` (default 5) + `PasswordPolicy.max_age_days` (default 0); `PasswordPolicy.validate()` checks last N bcrypt hashes; `UserRepository.add_password_history()`, `.get_password_history()`, `.is_password_expired()`; `get_current_user()` raises HTTP 403 `password_expired` when policy max_age exceeded.)

**Phase 3 — Advanced identity**

- [x] Just-in-time user provisioning from IdP claims.
  (`src/docreview360/jit_provisioning.py`: `jit_enabled()` env flag; `_extract_username()` with configurable `DOCREVIEW360_JIT_USERNAME_CLAIM`; `_extract_roles()` with `DOCREVIEW360_JIT_ROLE_MAP` JSON mapping + `DOCREVIEW360_JIT_DEFAULT_ROLES`; `provision_user_from_claims()` creates/syncs user + roles + audit log; integrated in OIDC callback and PIV/WebAuthn flows.)
- [x] SCIM 2.0 endpoint for user and group lifecycle management.
  (`src/docreview360/api/scim_router.py`: `APIRouter(prefix="/scim/v2")`; Bearer token auth via `DOCREVIEW360_SCIM_BEARER_TOKEN`; full CRUD on Users (`GET/POST /Users`, `GET/PUT/PATCH/DELETE /Users/{id}`); Groups as roles (`GET /Groups`, `GET /Groups/{id}`); `GET /ServiceProviderConfig`, `GET /Schemas`; registered in `api/__init__.py`.)
- [x] Separation of duties enforcement.
  (`src/docreview360/sod.py`: `SoDViolationError`, `SodRule` dataclass, pluggable rule registry; `check_approval_sod(user_id, document_id, workflow_id)` collects all violations; default rules: `no_self_approval` (user cannot approve their own uploaded doc), `no_workflow_creator_approval` (creator cannot be sole approver), `role_conflict` (configurable via `DOCREVIEW360_SOD_ROLE_CONFLICTS` JSON env var); `list_sod_rules()` + `set_sod_rule_enabled()` management helpers.)

### 38) Multi-tenant data isolation and database hardening

**Phase 1 — Tenant isolation**

- [x] Enforce organization-scoped data access across content tables.
  (`org_id` added to `ProjectModel`; `_enforce_project_access()` and `_enforce_project_manage_access()`
  enforce org membership for projects with an `org_id`; auto-assigned from creator's org on creation.
  `UserSessionRecord` and `OIDCStateRecord` models added to `models.py`.)
- [x] Add PostgreSQL row-level security as defense in depth.
  (`src/docreview360/db_rls.py`: `install_rls_policies(conn)` creates per-table `rls_org_isolation_<table>` policies using `app.current_org_id` session variable; `set_rls_org_context(conn, org_id)` sets the session variable; `verify_rls_active(conn)` returns RLS status per table for health checks; no-op on non-PostgreSQL backends. Tests in `tests/test_item38_database.py::TestDbRls`.)
- [x] Add schema-per-tenant option for customers that require physical isolation.
  (`Database.tenant_session(tenant_schema)` in `database.py`: context manager that applies `schema_translate_map={None: tenant_schema}` execution option, rewriting all unqualified table references to the tenant schema. Tests in `TestTenantSchema`.)
- [x] Adopt Alembic migration framework with rollback support.
  (`alembic.ini` at project root; `alembic/env.py` reads `DOCREVIEW360_DATABASE_URL`, imports `Base.metadata` for `--autogenerate` support; `alembic/versions/001_baseline.py` no-op root anchor; `alembic/script.py.mako` migration template. Existing deployments: `alembic stamp 001_baseline`. `alembic = ["alembic>=1.14"]` optional dep added. Tests in `TestAlembicSetup`.)

**Phase 2 — Enterprise database support**

- [x] Add Microsoft SQL Server support.
  (`database.default_url("mssql")` returns `mssql+pyodbc://...` URL; `mssql = ["pyodbc>=5.0"]` optional dep in `pyproject.toml`. Tests in `TestDefaultUrl::test_mssql_url`.)
- [x] Add Oracle Database support.
  (`database.default_url("oracle")` returns `oracle+oracledb://...` URL; `oracle = ["oracledb>=2.0"]` optional dep in `pyproject.toml`. Tests in `TestDefaultUrl::test_oracle_url`.)
- [x] Expose connection pooling configuration per environment.
  (`Database.__init__()` now reads `DOCREVIEW360_DB_POOL_SIZE` (default 10), `DOCREVIEW360_DB_MAX_OVERFLOW` (default 20), `DOCREVIEW360_DB_POOL_TIMEOUT` (default 30), `DOCREVIEW360_DB_POOL_RECYCLE` (default -1) from environment. Tests in `TestConnectionPooling`.)
- [x] Add column-level encryption for sensitive fields.
  (`src/docreview360/db_encryption.py`: `EncryptedString` SQLAlchemy TypeDecorator using AES-256-GCM; key from `DOCREVIEW360_COLUMN_ENCRYPTION_KEY` (64 hex chars); ciphertext format `enc:v1:<base64(nonce+ct)>`; fails open (no data loss on errors); `encryption_available()` helper. Tests in `TestDbEncryption` — 9 cases including roundtrip, nonce uniqueness, key-removal fallback.)

**Phase 3 — Data governance**

- [x] Add data retention policies.
  (`src/docreview360/data_retention.py`: `RetentionPolicy` dataclass with env-var-driven periods (`DOCREVIEW360_RETAIN_*_DAYS`); `run_retention_pass(policy)` purges user_sessions, oidc_states, audit_logs (only when explicitly configured); `RetentionResult.total` summary; audit log deletion bypasses WORM guard via `allow_audit_log_mutations=True`. Tests in `TestDataRetention` — 7 cases.)
- [x] Make audit logs append-only with cryptographic chaining at the database level.
  (Already in place: SQLite `BEFORE UPDATE/DELETE` triggers in `005_add_audit_log_hash_chain.sql`; SHA-256 hash chain with `prev_hash` written by `log_event()` in `logs/_dispatch.py`. New: `verify_audit_log_chain()` in `logs/_query.py` / exported from `logs/__init__.py` — verifies every entry's `prev_hash` links correctly to the previous entry's `hash`. Tests in `TestAuditLogChain` — 4 cases including tamper detection.)
- [x] Add automated encrypted database backup guidance.
  (`scripts/db_backup.sh`: auto-detects SQLite/PostgreSQL from `DOCREVIEW360_DATABASE_URL`; dumps via `sqlite3`/`pg_dump`; pipes through `gzip | openssl enc -aes-256-cbc -pbkdf2`; requires `BACKUP_PASSPHRASE` env var; includes restore command in output.)

### 39) Deployment, infrastructure, and operations

**Phase 1 — Container and orchestration hardening**

- [x] Move to a multi-stage Dockerfile and run as non-root.
  (3-stage build: frontend-builder → python-deps → runtime; non-root user `docreview:1001`; HEALTHCHECK via `/health/live`.)
- [ ] Add a Helm chart.
- [ ] Add Kubernetes manifests.
- [x] Split health endpoints into health, ready, and live.
  (`GET /health` (existing), `GET /health/live` (liveness probe), `GET /health/ready` (readiness + DB check).)

**Phase 2 — Enterprise operations**

- [ ] Add reverse proxy examples with WebSocket support.
- [ ] Add distributed Redis-backed rate limiting.
- [ ] Add structured JSON logging with correlation IDs.
- [ ] Add OpenTelemetry tracing.

**Phase 3 — Air-gap and high availability**

- [ ] Add an air-gap deployment guide.
- [ ] Add a production Docker Compose stack.
- [ ] Document blue-green or rolling deployment steps.
- [ ] Add a disaster recovery runbook with RTO and RPO targets.

### 40) Compliance, records management, and accessibility

**Phase 1 — Federal compliance**

- [ ] Document FIPS 140-2 validated cryptography usage.
- [ ] Add FedRAMP and FISMA control mapping.
- [ ] Ensure audit log completeness for all critical actions.
- [ ] Add NARA records management metadata.

**Phase 2 — Legal and eDiscovery**

- [ ] Add legal hold support.
- [ ] Add eDiscovery export.
- [ ] Add long-term digital signature compliance support.

**Phase 3 — Accessibility and internationalization**

- [ ] Add Section 508 and WCAG 2.1 AA scanning and audit coverage.
- [ ] Add internationalization framework and locale-aware formatting.
- [ ] Add configurable branding and terminology overrides.

### 41) Editor, integrations, and content management

**Phase 1 — Enterprise content integrations**

- [ ] Expand SharePoint Online integration.
- [ ] Add Confluence integration.
- [ ] Add Google Drive integration.
- [ ] Add Microsoft 365 co-authoring via WOPI.

**Phase 2 — Editor hardening**

- [ ] Add WebSocket proxy support guidance and fallback behavior.
- [ ] Add plugin sandboxing.
- [ ] Add offline editing support.
- [ ] Expand import and export format fidelity.

**Phase 3 — Enterprise search and analytics**

- [ ] Add OpenSearch or Elasticsearch-backed full-text search.
- [ ] Add analytics dashboard and exportable reports.
- [ ] Define API gateway compatibility and versioning strategy.

### 42) Configuration and extensibility

- [ ] Add hierarchical configuration: system defaults, organization overrides, project overrides.
- [ ] Add per-organization feature flags.
- [x] Expand the webhook event system with lifecycle events, signatures, and retries.
  (HMAC-SHA256 signing on outgoing deliveries (`X-DocReview360-Signature: sha256=<digest>`);
  auto-generated signing secret returned once on subscription creation; delivery count + last status tracking;
  `GET /webhooks/subscriptions`, `DELETE /webhooks/subscriptions/{id}` management endpoints;
  `project.created` and `document.created` lifecycle events emitted from routers;
  `emit_lifecycle_event()` API for any event type. Retry + backoff already in `event_dispatcher.py`.)
- [ ] Allow organization-defined custom workflows without code changes.
- [ ] Allow organization-defined custom fields without schema changes.
- [ ] Add theme and white-label support.
