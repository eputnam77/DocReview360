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
- [ ] Decide whether `frontend/document_types.json`, `frontend/phases.json`, and
  `frontend/phase_workflow_links.json` are still needed. Remove or ignore them if not.
  (Added to `.gitignore`, but the three files are still tracked in git as of 2026-03-10.)
- [ ] Remove or ignore `frontend/pages__backup_js_*` before release.
  (Added to `.gitignore`, but the backup trees are still tracked in git as of 2026-03-10.)

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

### 19a) AI-assisted automation candidates

- [ ] Evaluate `karpathy/autoresearch` as a pattern source, not a drop-in dependency. Use it only if each loop has a single target metric, a fixed run budget, and an objective pass or fail gate.
- [ ] Keep AI automation scoped to repository quality work. Ignore GitHub release publishing, PyPI publishing, Docker push, and other external release side effects unless a human explicitly enables them.
- [ ] Add a local "release shepherd" loop that reads `RELEASE_CHECKLIST.md`, picks 1 unchecked item, attempts a minimal change, runs only the required checks, and writes a short outcome report.
- [ ] Require artifact-based state for every autonomous run: prompt text, selected files, commands run, exit codes, test results, diff summary, and stop reason under `artifacts/automation/`.
- [ ] Define hard AI guardrails before any autonomous loop: approved model list, max turns, max tokens, retry limit, fallback model, writable path allowlist, and mandatory human review for high-risk files.
- [ ] Add a lockfile or lease so only 1 automation loop edits the repo at a time.
- [ ] Add a watchdog that stops the loop after repeated no-op diffs, repeated failing tests, or budget exhaustion.
- [ ] Prototype a Raspberry Pi-friendly runner for headless loops with a shell wrapper, lockfile, and append-only logs instead of relying on `cron` or `systemd`.
- [ ] Add custom Claude Code commands for repeatable maintenance tasks such as `/triage-failure`, `/docs-drift`, `/packaging-audit`, `/release-shepherd`, and `/checklist-next`.
- [ ] Use Claude Code hooks to enforce "read tests first" and "run verification before write" for autonomous maintenance commands.
- [ ] Build a failing-test triage loop that watches `pytest`, Playwright, and E2E failures, clusters similar stack traces, drafts the likely root cause, and proposes the smallest patch.
- [ ] Build a flaky-test hunter that reruns smoke tests multiple times, captures artifacts, and ranks failures by frequency and first bad commit if git history is available.
- [ ] Build a docs drift checker that compares `README.md`, `docs/`, `pyproject.toml`, env var docs, Docker docs, and frontend scripts for mismatched commands, versions, and URLs.
- [ ] Build a packaging auditor that inspects wheel, sdist, and Docker contents and flags shipped tests, placeholders, internal files, or runtime junk before release.
- [ ] Build a placeholder and metadata reviewer that finds `example.com`, `info@example.com`, stale license text, inconsistent versions, and public repo readiness gaps.
- [ ] Build a dependency-review loop that summarizes `pip-audit`, `semgrep`, `bandit`, `trivy`, and `npm audit` output into actionable issues instead of raw scanner logs.
- [ ] Build a security-defaults reviewer focused on auth, OIDC, Keycloak, secrets, token lifetimes, and production-safe env defaults.
- [ ] Build a deployment drift checker that compares `Dockerfile`, `docker-compose*.yml`, Helm, Kubernetes manifests, and `docs/deployment.md` for inconsistent ports, env vars, health checks, and image tags.
- [ ] Build a performance regression loop that reruns `scripts/measure_performance_baseline.py`, compares results to `docs/performance_baseline.md`, and opens a focused fix task when thresholds regress.
- [ ] Build an accessibility loop for the Next.js frontend that runs axe or Playwright-based checks, captures screenshots, and drafts small UI fixes for obvious regressions.
- [ ] Build a UX smoke-review loop that logs in as `alice` and `bob`, exercises document upload and approval flows, then summarizes friction, broken states, and missing error messages.
- [ ] Build an audit-log integrity loop that verifies append-only behavior, hash-chain validation, retention settings, and backup restore steps after risky backend changes.
- [ ] Build an ML packaging verifier that compares PyTorch and ONNX outputs on a fixed fixture set, validates model metadata, and blocks model packaging when drift exceeds the threshold.
- [ ] Build a release-note drafter that reads merged commits, checklist changes, and user-visible diffs, then prepares a draft changelog for human review only.
- [ ] Build an issue-grooming loop that turns repeated failures or review findings into deduplicated GitHub issues with severity, repro steps, and file references.
- [ ] If `autoresearch` is trialed, start with read-only or report-only tasks first. Do not let it write code until its summaries are consistently useful on this repo.
- [ ] If `autoresearch` is trialed, restrict it to narrow surfaces such as docs drift, packaging review, flaky test analysis, or performance triage before attempting broader "improve the app" loops.

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
  (`DOCREVIEW360_WORKFLOW_TEMPLATES_FILE` removed from `src/docreview360/e2e_runtime.py`; replaced with a comment noting the DB-only persistence.)

**43c) Duplicate API registration remains**

- [ ] Keep the router-based implementation or the legacy monolith, but not both.

**43d) Frontend API migration is incomplete**

- [x] Replace remaining protected-page raw `fetch(...)` calls with `authenticatedFetch(...)`.
  (All 38 raw fetch calls in pages/ migrated; login.tsx intentionally kept as raw fetch.)
- [ ] Broaden the frontend raw-fetch guard so it catches `fetch(`${API}/...`)`.
  (Remaining: pages with `authenticatedFetch(\`${API}/...\`)` work correctly but could use relative paths.)

**43e) `filelock` cleanup is not complete**

- [x] Remove remaining `filelock` runtime usage.
  (`filelock` was removed from `requirements.txt` and `src/docreview360.egg-info/{PKG-INFO,requires.txt}`; `tests/test_release_checklist_auth_and_frontend.py` now asserts it is absent from release metadata.)

**43f) Plugin marketplace frontend/backend contract mismatch**

- [x] Add the missing plugin marketplace routes or remove the frontend calls.
  (Added `GET /plugin-marketplace/builtin-status` and `POST /plugin-marketplace/toggle` to `admin_router.py`;
  added `get_builtin_status()` and `set_builtin_plugin_state()` to `plugin_marketplace.py`.)

## Product and architecture backlog

### Document version lineage

- [x] Branch and merge support for parallel review tracks.
  (`src/docreview360/api/branches_router.py`: 6 endpoints — POST/GET `/documents/{id}/branches`, GET/PUT `/documents/{id}/branches/{bid}`, POST merge (creates `DocumentVersion`, updates `doc.content`), POST close; `DocumentBranch` model in `models.py`; 8 passing tests in `tests/test_document_branches.py`.)

### 30) Large modules needing decomposition

- [x] Decompose remaining large modules: `logs.py` → `logs/` package (`_db.py`, `_dispatch.py`, `_query.py`, `__init__.py`); `reporting.py` → `reporting/` package (`_models.py`, `_metrics.py`, `_reports.py`, `__init__.py`). All public APIs preserved via `__init__.py` re-exports.
- [ ] Decompose remaining large modules: `auth.py`, `search.py`, `workflows.py`, `doc_types.py`, `documents.py` (lower priority, defer to post-v0.2).

### 31) Frontend state management

- [x] Introduce centralized server-state handling: React Query (`@tanstack/react-query`) configured in `_app.tsx` with global `staleTime`, `gcTime`, retry, and `refetchOnWindowFocus` defaults.
- [x] New hooks in `frontend/lib/`: `useProjects.ts`, `useDocuments.ts`, `useNotifications.ts`, `useSessions.ts` — all using `authenticatedFetch`, optimistic updates, and shared cache keys.
- [x] Migrate remaining pages from inline `fetch()` to the new hooks.
  (`frontend/pages/projects/index.tsx` and `frontend/pages/dashboard/index.tsx` now load project state through `useProjects()`, and `frontend/pages/projects/new.tsx` now creates projects through `useCreateProject()`; `tests/test_release_checklist_auth_and_frontend.py` asserts these hook-backed paths.)

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
  (Updated the stale `docreview360` rows from GPL/GPL-3.0-only to MIT; `tests/test_release_checklist_auth_and_frontend.py` now checks the report.)
- [x] Verified no vendored third-party code with incompatible licenses in `src/`.

### 37) Authentication and identity provider integration

**Phase 1 — Core SSO and directory**

- [x] Full OIDC and OAuth 2.0 provider integration with Authorization Code + PKCE.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers both `GET /oidc/authorize` and `GET /oidc/callback` for the PKCE flow.)
- [x] LDAP and Active Directory integration with LDAPS and group-to-role mapping.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers `ldap_login()` across authentication plus group-to-role mapping.)
- [x] SAML 2.0 SP support.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers the `/saml/login` redirect and `/saml/acs` assertion-consumer flow.)
- [x] Session management hardening: idle timeout, absolute lifetime, concurrent session limits, server-side revocation.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers idle timeout, expired-session cleanup, concurrent-session revocation, and the `/sessions` list/revoke endpoints; `oidc_client.list_user_sessions()` was also fixed to inactivate expired rows.)

**Phase 2 — Federal and DoD authentication**

- [x] CAC/PIV smart card authentication.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers `POST /piv/verify`, including JIT provisioning and RBAC role assignment.)
- [x] FIDO2 and WebAuthn support.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers the WebAuthn registration and authentication endpoint flows.)
- [x] Password policy enforcement with history, expiry, and lockout controls.
  (`tests/auth/test_password_policy.py` and `tests/test_auth_repository.py` still cover reuse/lockout; `tests/test_release_checklist_auth_and_frontend.py` now adds direct password-expiry coverage.)

**Phase 3 — Advanced identity**

- [x] Just-in-time user provisioning from IdP claims.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers `jit_provisioning.provision_user_from_claims()` for user creation plus role sync.)
- [x] SCIM 2.0 endpoint for user and group lifecycle management.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers `/scim/v2/Users` create/patch and `/scim/v2/Groups/{group_id}` membership lookup.)
- [x] Separation of duties enforcement.
  (`tests/test_release_checklist_auth_and_frontend.py` now covers `sod.check_approval_sod()` raising on a no-self-approval violation.)

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
- [x] Add a Helm chart.
  (`helm/docreview360/`: `Chart.yaml`, `values.yaml`, templates for Deployment, Service, Ingress, ConfigMap, HPA, ServiceAccount, `_helpers.tpl`; liveness/readiness probes on `/health/live` and `/health/ready`; non-root security context; WebSocket Upgrade annotations on Ingress; `autoscaling/v2` HPA; secrets section with placeholder values. Tests in `TestHelmChart` — 14 cases.)
- [x] Add Kubernetes manifests.
  (`k8s/`: `namespace.yaml`, `deployment.yaml` (non-root, drop ALL caps, liveness+readiness probes), `service.yaml`, `ingress.yaml` (WebSocket annotations), `configmap.yaml`, `hpa.yaml`, `kustomization.yaml`. Tests in `TestK8sManifests` — 13 cases.)
- [x] Split health endpoints into health, ready, and live.
  (`GET /health` (existing), `GET /health/live` (liveness probe), `GET /health/ready` (readiness + DB check).)

**Phase 2 — Enterprise operations**

- [x] Add reverse proxy examples with WebSocket support.
  (`nginx/nginx.conf`: HTTP→HTTPS redirect; TLS 1.2/1.3; WebSocket `/ws/` location with `Upgrade`/`Connection` headers; `proxy_read_timeout 3600s`; security headers (HSTS, X-Frame-Options, CSP); `/metrics` restricted to internal network; health location with no access logging. Tests in `TestNginxConfig` — 6 cases.)
- [x] Add distributed Redis-backed rate limiting.
  (`src/docreview360/rate_limiter.py`: sliding-window counter using Redis sorted set (`ZADD`/`ZREMRANGEBYSCORE`); in-memory `threading.Lock`-protected fallback; `check_rate_limit(key, limit, window)` API; `rate_limit_dep()` FastAPI dependency factory returning HTTP 429 with `Retry-After`; configurable via `DOCREVIEW360_RATE_LIMIT_ENABLED/DEFAULT/WINDOW` and `DOCREVIEW360_REDIS_URL`. Tests in `TestRateLimiter` — 8 cases.)
- [x] Add structured JSON logging with correlation IDs.
  (`src/docreview360/structured_logging.py`: `StructuredJsonFormatter` emitting single-line JSON with `timestamp`, `level`, `logger`, `message`, `service`, `trace_id` (from `TRACE_ID` ContextVar), `extra`, `exc_info`; `setup_structured_logging(level, service, force)` installs formatter on root logger; env flag `DOCREVIEW360_STRUCTURED_LOGGING`. Tests in `TestStructuredLogging` — 10 cases.)
- [x] Add OpenTelemetry tracing.
  (`src/docreview360/telemetry.py`: optional `opentelemetry-sdk`+`opentelemetry-exporter-otlp-proto-grpc` deps (`[otel]` extra); `setup_telemetry()` configures `TracerProvider` + `OTLPSpanExporter` + `BatchSpanProcessor`; `get_tracer(name)` returns live or `_NoopTracer`; `_NoopSpan`/`_NoopTracer` for graceful degradation; `DOCREVIEW360_OTEL_ENABLED/SERVICE_NAME/EXPORTER_OTLP_ENDPOINT` env vars. Tests in `TestTelemetry` — 6 cases.)

**Phase 3 — Air-gap and high availability**

- [x] Add an air-gap deployment guide.
  (`docs/air_gap_deployment.md`: image export/load/push to internal registry; Python wheel bundle; docker-compose.airgap.yml overlay; Helm air-gap values; required env vars; disabling external dependency calls. Tests in `TestDeploymentDocs`.)
- [x] Add a production Docker Compose stack.
  (`docker-compose.prod.yml`: web + worker + beat + nginx + PostgreSQL + Redis; named volumes; internal/proxy network split; all services with health checks; `.env.prod` referenced; Celery beat scheduler; nginx mounts `nginx/nginx.conf`. Tests in `TestDockerComposeProd` — 8 cases.)
- [x] Document blue-green or rolling deployment steps.
  (`docs/blue_green_deployment.md`: full blue-green Docker Compose procedure (deploy green, health check, nginx switch, retire blue, rollback); Kubernetes rolling update (`kubectl set image`, `rollout status`, `rollout undo`); Helm upgrade/rollback; database migration safety (expand-contract). Tests in `TestDeploymentDocs`.)
- [x] Add a disaster recovery runbook with RTO and RPO targets.
  (`docs/disaster_recovery.md` extended: RTO 4h / RPO 1h tiered table; DB restore from encrypted backup (SQLite + PostgreSQL); Redis recovery procedure; audit log chain verification post-recovery; communication timeline; DR test schedule. Tests in `TestDeploymentDocs` — 3 cases.)

### 40) Compliance, records management, and accessibility

**Phase 1 — Federal compliance**

- [x] Document FIPS 140-2 validated cryptography usage.
  (`docs/fips_fedramp_compliance.md`: cryptography table covering JWT/HS256, AES-256-GCM, SHA-256, TLS 1.2/1.3, bcrypt; `DOCREVIEW360_FIPS_MODE` env var documented.)
- [x] Add FedRAMP and FISMA control mapping.
  (`docs/fips_fedramp_compliance.md`: NIST SP 800-53 control mapping table — AC-2, AC-3, AU-2, AU-9, IA-2, IA-5, SC-28, SI-12, CP-9.)
- [x] Ensure audit log completeness for all critical actions.
  (`GET /admin/audit/completeness` in `admin_router.py` calls `verify_audit_log_chain()` from `logs/__init__.py` and returns chain integrity status; requires admin role. Tested in `TestAuditCompletenessEndpoint`.)
- [x] Add NARA records management metadata.
  (`src/docreview360/nara_metadata.py`: `NaraMetadata` model; `get_nara_metadata()`, `set_nara_metadata()` (upsert), `delete_nara_metadata()`, `list_vital_records()`, `list_records_due_disposal()`; 4 passing tests in `tests/test_item40_compliance.py::TestNaraMetadata`.)

**Phase 2 — Legal and eDiscovery**

- [x] Add legal hold support.
  (`src/docreview360/legal_hold.py`: `LegalHold` + `LegalHoldDocument` models; `create_legal_hold()`, `add_document_to_hold()`, `remove_document_from_hold()`, `release_hold()`, `is_document_on_hold()`, `list_legal_holds()`, `get_document_holds()`; API in `src/docreview360/api/legal_router.py` with 7 endpoints. 5 passing tests in `TestLegalHold`.)
- [x] Add eDiscovery export.
  (`src/docreview360/ediscovery.py`: `export_ediscovery()` creates ZIP with per-document `content.txt`, `metadata.json`, `audit_log.csv`, and a top-level `manifest.json`; `POST /legal/ediscovery/export` endpoint; 2 passing tests in `TestEDiscovery`.)
- [ ] Add long-term digital signature compliance support.

**Phase 3 — Accessibility and internationalization**

- [x] Add Section 508 and WCAG 2.1 AA scanning and audit coverage.
  (`src/docreview360/accessibility.py`: `scan_document_accessibility()` checks WCAG 1.1.1 (alt text), 1.3.1 (heading order), 2.4.4 (link text), 3.1.1 (lang attr), 4.1.2 (form labels); returns `AccessibilityScanResult` with score [0–100] and violations list; `POST /tools/accessibility-scan` endpoint in `tools_router.py`; `docs/section508_wcag.md` coverage table. 5 passing tests in `TestAccessibilityScan`.)
- [x] Add internationalization framework and locale-aware formatting.
  (`src/docreview360/i18n.py`: `translate(key, locale)`, `detect_locale(accept_language)`, `format_date(dt, locale)`, `list_locales()`, `get_namespace(ns, locale)`; 4 supported locales (en/es/fr/de); `GET /i18n/locales`, `GET /i18n/translations/{locale}` API endpoints; locale JSON files in `frontend/public/locales/{en,es,fr,de}/common.json`; Next.js `i18n` config in `next.config.js`. 13 passing tests in `tests/test_item40_i18n_branding.py::TestI18n`.)
- [x] Add configurable branding and terminology overrides.
  (`src/docreview360/branding.py`: `get_branding()`, `set_branding()`, `reset_branding()`, `get_terminology()`, `set_terminology()`, `reset_terminology()`, `get_full_theme()`; stored via `OrgConfig` under `branding.*`/`terminology.*` keys; hex colour and URL validation; `GET/PUT/DELETE /orgs/{id}/branding`, `PUT /orgs/{id}/terminology` API endpoints. 13 passing tests in `TestBranding` + `TestBrandingAPI`.)

### 41) Editor, integrations, and content management

**Phase 1 — Enterprise content integrations**

- [x] Expand SharePoint Online integration.
  (Existing `integrations/sharepoint_upload.py` uploads signed PDFs, certificates, and metadata; `async_client_from_env()` reads `SHAREPOINT_*` env vars; `SHAREPOINT_SIGNED_FOLDER`/`SHAREPOINT_CERT_FOLDER` configurable.)
- [x] Add Confluence integration.
  (`src/docreview360/integrations/confluence_integration.py`: `ConfluenceClient` with list/get/create/update/delete page, full-text search (CQL), `export_page_as_markdown()`, `import_document()`; Markdown↔storage-format converters; `client_from_env()` from `CONFLUENCE_*` env vars. 5 passing tests in `tests/test_item41_integrations.py::TestConfluenceIntegration`.)
- [x] Add Google Drive integration.
  (`src/docreview360/integrations/google_drive_integration.py`: `GoogleDriveClient` with list/search/get/download/export/upload/update/delete/share; multipart upload; `export_google_doc()` (PDF/DOCX/CSV); service-account auth via `google-auth` or direct `GOOGLE_DRIVE_ACCESS_TOKEN`; `client_from_env()`. 4 passing tests in `TestGoogleDriveIntegration`.)
- [ ] Add Microsoft 365 co-authoring via WOPI.

**Phase 2 — Editor hardening**

- [x] Add WebSocket proxy support guidance and fallback behavior.
  (`docs/websocket_proxy_guide.md`: nginx, Caddy, AWS ALB, Kubernetes Ingress configuration; `/ws/collab`, `/ws/notifications`, `/ws/comments` paths; fallback polling behavior when WebSocket unavailable; `NEXT_PUBLIC_DISABLE_WS=true` override. Test: `TestDocumentation.test_websocket_proxy_guide_exists`.)
- [x] Add plugin sandboxing.
  (`src/docreview360/plugin_sandbox.py`: `PluginSandbox` with three modes — `none` (direct), `restricted` (meta_path blocker + `_EVICT_MODULES` for already-loaded I/O modules, configurable timeout), `subprocess` (allow-list importer in isolated process); `SandboxedPluginLoader` registry with `register()`/`load()`/`run()`; `PluginManifest` dataclass; `default_loader` singleton. 9 passing tests in `TestPluginSandbox`.)
- [ ] Add offline editing support.
- [ ] Expand import and export format fidelity.

**Phase 3 — Enterprise search and analytics**

- [ ] Add OpenSearch or Elasticsearch-backed full-text search.
- [ ] Add analytics dashboard and exportable reports.
- [x] Define API gateway compatibility and versioning strategy.
  (`docs/api_versioning.md`: URL-path versioning (`/api/v1/`), additive-only change policy, deprecation timeline, `X-DocReview360-API-Version` response header, gateway compatibility table (AWS API Gateway, Kong, Apigee, Istio, nginx), rate limiting per version. Test: `TestDocumentation.test_api_versioning_doc_exists`.)

### 42) Configuration and extensibility

- [x] Add hierarchical configuration: system defaults, organization overrides, project overrides.
  (`src/docreview360/hierarchical_config.py`: `SYSTEM_DEFAULTS` dict (9 keys); `get_config()` resolves project → org → system; `OrgConfig` + `ProjectConfig` models; `set_org_config()`, `set_project_config()`, `get_org_config_all()`, `get_project_config_all()`, `delete_org_config()`, `delete_project_config()`; API in `config_router.py` (`GET/PUT/DELETE /config/org/{id}/{key}`, `/config/project/{id}/{key}`, `/config/system`). 5 passing tests in `TestHierarchicalConfig`.)
- [x] Add per-organization feature flags.
  (`src/docreview360/feature_flags.py` rewritten: `BUILT_IN_FLAGS` dict (16 flags); `FeatureFlag` model; `is_flag_enabled()` resolves org-specific → system-wide → built-in default; `_apply_rollout()` uses `hashlib.md5` for deterministic hash-based rollout; `set_flag()`, `list_flags()`, `delete_flag()`; API in `flags_router.py` (5 endpoints). 5 passing tests in `TestFeatureFlags`.)
- [x] Expand the webhook event system with lifecycle events, signatures, and retries.
  (HMAC-SHA256 signing on outgoing deliveries (`X-DocReview360-Signature: sha256=<digest>`);
  auto-generated signing secret returned once on subscription creation; delivery count + last status tracking;
  `GET /webhooks/subscriptions`, `DELETE /webhooks/subscriptions/{id}` management endpoints;
  `project.created` and `document.created` lifecycle events emitted from routers;
  `emit_lifecycle_event()` API for any event type. Retry + backoff already in `event_dispatcher.py`.)
- [x] Allow organization-defined custom workflows without code changes.
  (`src/docreview360/custom_workflows.py`: `CustomWorkflowTemplate` model; `create_custom_workflow()` with step validation (required fields, no duplicate names, positive SLA); `get_custom_workflow()`, `list_custom_workflows()`, `update_custom_workflow()`, `delete_custom_workflow()`; API in `config_router.py` (CRUD `/orgs/{id}/workflows`). 5 passing tests in `TestCustomWorkflows`.)
- [x] Allow organization-defined custom fields without schema changes.
  (`src/docreview360/custom_fields.py`: EAV pattern — `CustomFieldDefinition` + `CustomFieldValue` models; field types: text, number, date, boolean, select; `create_field_definition()`, `validate_field_value()`, `set_field_value()`, `get_field_values()`, soft `delete_field_definition()`; API in `config_router.py` (CRUD `/orgs/{id}/fields`, `GET/PUT /documents/{id}/custom-fields`, `GET/PUT /projects/{id}/custom-fields`). 5 passing tests in `TestCustomFields`.)
- [ ] Add theme and white-label support.
