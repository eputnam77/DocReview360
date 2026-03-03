# Changelog

All notable changes to DocReview360 are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

A schema-breaking change requires a MAJOR version bump.

---

## [Unreleased]

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
