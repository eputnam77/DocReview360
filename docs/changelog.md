# Changelog

All notable changes to DocReview360 are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

A schema-breaking change requires a MAJOR version bump.

---

## [Unreleased]

### Added

- **TipTap plugin architecture** (`frontend/extensions/registry.ts`): immutable `PLUGIN_REGISTRY` manifest with semver compatibility checker, `PLUGIN_CONTRACT` constants, and Vitest CI tests ensuring no core patching.
- **TipTap content schema validation** (`frontend/lib/contentSchema.ts`): `validateTipTapContent`, `parseTipTapContent`, `isContentValid`, `getContentValidationError` with 22 Vitest tests.
- **Documenso e-signature provider** (`src/docreview360/integrations/signature/documenso.py`): full `SignatureProvider` protocol implementation with circuit breaker, webhook processing, and PKI validation.
- **DocuSign enterprise connector** (`src/docreview360/integrations/signature/docusign.py`): eSign REST API v2.1 integration with Connect webhook support, circuit breaker, and 20 tests.
- **Notifications integrations** (`src/docreview360/notifications.py`): Slack, Teams, generic webhook, and email dispatcher. `GET/PUT /notifications/settings`, `POST /notifications/test`.
- **Multi-tenant organizations** (`src/docreview360/organizations.py`): full CRUD with per-org settings (max_users, allowed_doc_types, branding, custom_phases). `GET/PUT /organizations/{id}/settings`.
- **Regulatory citation checker** (`src/docreview360/regulatory.py`): regex-first extraction of 21 CFR, ISO, IEC, EU MDR/IVDR citations. `POST /ai/regulatory-check` endpoint.
- **Document version lineage**: `version_number` auto-increment, `frozen` field, `freeze_document/unfreeze_document`, `get_version_history`, `restore_document_version`. Endpoints: `GET /documents/{id}/versions`, `POST /documents/{id}/restore/{rev}`, `POST/DELETE /documents/{id}/freeze`.
- **Redline comparison** (`diff_document_revisions`): unified diff with `lines_added/removed`, `similarity_ratio`. `GET /documents/{id}/diff/{rev_a}/{rev_b}`.
- **Document converter rewrite** (`src/docreview360/document_converter.py`): real DOCX/MD/HTML/PDF conversion using python-docx and pypdf. `/tools/convert` returns file bytes with `Content-Disposition`.
- **Comment export to Word**: `GET /comments/{project_id}/export/docx` with python-docx, plain-text fallback.
- **Shareable project links**: `POST/GET/DELETE /share-links`, public `GET /share/{token}`. 32-byte random tokens with permission scopes and optional expiry.
- **API key management** (`src/docreview360/api_keys.py`): SHA-256 hashed keys, `POST/GET/DELETE /api-keys`.
- **Security headers middleware**: `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy` on all responses.
- **Frontend CSP headers** via `next.config.js` `headers()`.
- **Auth key rotation**: `SECRET_KEY_PREVIOUS` env var; `get_current_user()` falls back to old key during rotation window. Runbook in `docs/security/key-rotation.md`.
- **Audit HMAC key rotation**: `DOCREVIEW360_AUDIT_HMAC_KEY_PREVIOUS` env var; dual-key verification during rotation window.
- **Token revocation**: JTI blacklist in `auth.py`; `POST /logout` inserts JTI; all authenticated routes check revocation.
- **Server-side session generation**: `token_generation` column on users table; all tokens include `gen` claim; password change and account suspension invalidate all sessions.
- **Approvals package split**: `approvals.py` decomposed into `approvals/` package (`core.py`, `signatures.py`, `routing.py`) with full backward-compatible re-exports.
- **Monolithic API decomposed** into 7 sub-routers (`auth_router`, `projects_router`, `documents_router`, `workflows_router`, `admin_router`, `dashboards_router`, `tools_router`).
- **Deterministic DB migrations**: numbered SQL files in `migrations/` tracked by `schema_versions` table; idempotent apply.
- **AI optimization prompts documentation** (`docs/ai-optimization-prompts.md`): 8 sections with system/user prompt templates, tuning notes, and fallback strategies.
- **Phase configuration aligned** with Document Types schema: `PhaseWorkflowLinkModel` with `id`, `display_order`, `workflow_template_id`. `GET /phases/config` returns full metadata.
- **FedRAMP backup scheduling** (`security_hardening.py`): `enable_fedramp_backup` configures Celery beat task for encrypted daily backups.
- **Rate limiters** for document export, search, signature, and bulk operations.
- **WebSocket auth** for `/ws/logs`: token passed as query param, validated server-side.
- **`approve_by_initials` endpoint** for compact reviewer sign-off.
- **RBAC cache invalidation** with 5-second monotonic debounce.
- **Contributing section** added to README.

### Fixed

- `send_for_signature` now resets `document_hash` when re-linking an approval to a different document, preventing spurious hash-mismatch errors.
- `GET /sign/{sig_id}` made public (removed duplicate auth-gated route from `documents_router.py`).
- `POST /users/import` now accepts both JSON body and CSV file upload (FastAPI `File`/`Body` incompatibility resolved via raw `Request` body reading).
- `scripts/replay_webhook.py` replaced `requests` with `httpx` (project dependency).
- Audit log purge uses atomic write-then-rename (`os.replace`) to prevent truncation on crash.
- `eval()` in `tiptapMarkReview.ts` replaced with standard dynamic `import()`.
- Open redirect in `documenso/[sig].tsx` fixed with `new URL()` + origin comparison.
- Backend-supplied signature URL validated with `new URL()` + same-origin enforcement before `window.location.assign()`.
- `DEFAULT_SECRET_KEY` constant removed from `auth.py`; only `os.urandom()` fallback remains.

---

## [0.1.2] - 2026-03-03

### Added

- `CHANGELOG.md` — this file.
- PyPI classifiers, keywords, and `[project.urls]` in `pyproject.toml`.
- Third-party license attribution in `docs/licenses.md`.

### Fixed

- Removed duplicate `save_state()` stub in `doc_types.py` (shadowed by the full implementation).
- Removed unused `expected_version` and `previous_state` variables in `doc_types.py`.
- Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` in `secrets.py`.
- Updated corresponding test mocks in `test_secrets_additional.py` and `test_secrets_expiry_env_fallback.py`.
- Suppressed intentional `E402` import ordering in `api/__init__.py` (imports must follow `apply_e2e_run_dir()` side-effect call).
- Suppressed intentional `E402` import ordering in `test_api_ml.py` (stub definitions must precede module import for monkeypatching).
- Fixed 25 auto-fixable ruff lint errors (unsorted imports, unused imports) across `src/` and `tests/`.

---

## [0.1.1] - 2026-02-21

### Added

- E2E runner (`scripts/run_e2e.py`) with smoke and full test marks.
- E2E sandbox isolation: run-dir support and local run-ID format.
- `KEEP_E2E_ARTIFACTS` flag to retain logs and Playwright artifacts after a run.
- Aligned demo data between frontend and backend.

### Fixed

- Hardened sandbox-friendly E2E flow for reliability across environments.
- Isolated sandbox runner outputs to prevent cross-run contamination.

---

## [0.1.0] - 2026-01-15

### Added

**Core workflow**

- Document model with in-memory storage, MIME validation, and HTML sanitization via `bleach`.
- Approval state machine (`pending` → `approved` / `rejected`) with sequential and parallel step modes.
- Workflow templates and phase-based step progression (`workflow_engine.py`).
- Phase gating: sequential approvals block advancement until the current step resolves.

**Authentication and authorization**

- JWT authentication (HS256) with configurable issuer, audience, and token TTL.
- OIDC token flow at `/oidc/token` and `/oidc/me`.
- bcrypt password hashing and TOTP-based MFA support (`DOCREVIEW360_REQUIRE_MFA`).
- Role-based access control backed by a SQLite `RoleRepository`; `require_permission()` FastAPI dependency.
- Account lockout after configurable failed login attempts (`DOCREVIEW360_MAX_FAILED_ATTEMPTS`, `DOCREVIEW360_LOCKOUT_SECONDS`).
- CSRF protection via `X-CSRF-Token` header when using HTTP-only cookies.
- Demo users seeded automatically in `dev` / `test` environments (`alice` admin, `bob` auditor).

**Digital signatures**

- Signature provider abstraction with `sandbox`, `documenso`, and `local` backends.
- Provider failover chain via `SIGNATURE_PROVIDER_FALLBACK`.
- Document content hash frozen at approval time; hash validated before signature finalization.
- Documenso webhook handler at `POST /hooks/documenso`.

**Audit trail**

- HMAC-chained `AuditLogEntry` records with WORM semantics.
- Immutable audit log with retention policy and exportable audit package.
- Phase-based audit snapshots.

**API**

- FastAPI application with auto-generated interactive docs at `/docs`.
- Versioned aliases at `/api/v1/*` alongside root-level routes.
- OpenAPI schema snapshot test in CI.
- Rate limiting on token, login, and upload endpoints.
- CORS allowlist via `DOCREVIEW360_ALLOW_ORIGINS`.

**ML pipeline**

- PyTorch model training (`docreview360 ml train`) and ONNX export (`docreview360 ml export`, opset 18).
- Dynamic and static INT8 quantization options.
- ONNX inference via `CPUExecutionProvider` by default; GPU and MPS providers optional.
- Signature anomaly detection model.
- Quality critic ONNX model for document review suggestions.
- ML artifact packaging (`docreview360 ml package`) and hot-swap via `DOCREVIEW360_ML_MODEL_DIR`.

**CLI**

- `docreview360 init` — interactive setup wizard generating `docreview360.yaml`.
- `docreview360 migrate export/import` — portable backup/restore.

**Frontend**

- Next.js 13+ React application with TipTap rich-text editor.
- Login, dashboard, project creation, editor, and review tracker pages.
- Global page footer with version, build date, environment, and copyright.

**Observability and deployment**

- Structured JSON production logs with request correlation IDs.
- Prometheus metrics endpoint.
- `DOCREVIEW360_ENV=production` mode enforces required secrets at startup.
- Docker image and `docker-compose.yml` with Postgres, OpenSearch, and Redis.
- Encryption at rest for archived artifacts (AES-GCM).

**Governance**

- `TERMS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.
- SBOM generation (CycloneDX) per release artifact.
- GPG/Sigstore release tag signing.
- OCI metadata labels on Docker images.
- Performance baseline recorded in `docs/performance_baseline.md`.

---

[Unreleased]: https://github.com/eputnam77/DocReview360/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/eputnam77/DocReview360/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/eputnam77/DocReview360/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/eputnam77/DocReview360/releases/tag/v0.1.0
