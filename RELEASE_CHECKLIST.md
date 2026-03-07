# DocReview360 Release Checklist (First Public Release)

Target window: next month (confirm exact date and time zone).

Recommended v0.1 strategy:

âœ… GitHub Release (required)
âœ… PyPI (CLI-first distribution)
ðŸ”¶ Docker (optional but recommended if full stack is core value)


**WANT TO ADD**
Youâ€™re at the stage where clarity + product positioning matter as much as features.

Given that youâ€™re preparing DocReview360 for public release (and potentially positioning it as a serious document review platform, not just an internal tool), Iâ€™d refine your list into:

1. Clear feature objectives
2. Platform integrity safeguards
3. Workflow/UX improvements
4. Enterprise-readiness features
5. Competitive differentiators

Below is a cleaned-up and expanded version of your list â€” followed by additional strategic ideas.

---

# Refined + Clarified Feature Roadmap (DocReview360)

## 1. Authoring & Templates

* [x] Implement structured document templates using TipTap (modular, version-controlled)
* [ ] Keep TipTap core unmodified (consume directly from upstream repo; extend via plugins only)
* [ ] Establish update-safe plugin architecture to allow future TipTap upgrades without breakage
* [ ] Ensure authoring tools persist cleanly to CMS (schema validation + version snapshots)
* [x] Add template version history and change tracking
* [x] Allow template locking per project phase

---

## 2. Configuration & Workflow Architecture

* [ ] Standardize Configuration/Phases schema to match Document Types schema
* [ ] Allow dynamic phase configuration per document type
* [x] Enable workflow-driven approvals table (users added dynamically, not hardcoded)
* [x] Redesign Project View:

  * Visual workflow timeline
  * Phase status indicators
  * Embedded approvals grid
  * Clean, minimal UI
* [x] Add reviewer comment section directly in Project View
* [x] Ensure phase gating logic (cannot advance without required approvals)
* [ ] Add shareable project URL links with permission-aware access
* [x] Add viewer-only project role and access controls
* [x] Add administrator branding settings in Configuration to replace default product mark with company logo and company name
* [x] Enforce branding guardrails (image size/type limits, alt text, and safe fallback to default DocReview360 branding)

---

## 3. Review & Signature Layer

* [ ] Support Documenso as default e-signature provider
* [ ] Add DocuSign integration as optional enterprise connector
* [x] Abstract signature provider behind provider interface (future-proofing)
* [x] Log signature events into audit trail
* [x] Add approve by initials (as in First initial Last initial, "EP")

---

## 4. Dashboard & Visibility

* [x] Restore full dashboard view array (project status, overdue reviews, approval state)
* [x] Add executive summary dashboard (for leadership view)
* [x] Add reviewer workload dashboard
* [x] Add document aging metrics
* [x] Add SLA tracking per phase
* [x] Add a global page footer across all DocReview360 pages with product/company name, release build number, build date, environment, and copyright
* [x] Add footer links for support/docs and security/privacy pages

---

## 5. Review Experience Enhancements

* [x] Inline reviewer commenting (threaded)
* [x] Structured comment tagging (legal, style, technical, policy, etc.)
* [x] Reviewer disposition workflow (open â†’ resolved â†’ accepted â†’ rejected)
* [ ] Comment export to Word (for legacy workflows)
* [ ] Add document converter support (Word, Markdown, PDF)
* [ ] Redline comparison view (document version diff)

---

# Strategic Additions (High Impact)

Based on your broader ecosystem and FAA-heavy background, these could differentiate DocReview360 significantly.

---

## A. Audit & Compliance Engine

* [x] Immutable audit log
* [x] Phase-based audit snapshots
* [x] Exportable audit package (PDF + JSON)
* [x] Role-based permission matrix visualization
* [ ] Verification override logging (you already have RBAC structure â€” extend it)

This aligns well with federal compliance workflows.

---

## B. AI-Assisted Review (Optional Layer)

Given your ScriptCore and style validator background:

* [x] AI style validation pass (toggleable)
* [ ] Define and document optimization prompts for document workflows (TBD scope)
* [x] Acronym validation check
* [x] Heading structure validation
* [x] Plain language scoring
* [ ] Regulatory citation checker
* [x] â€œPre-flightâ€ validation before phase advancement

Make this optional and clearly separated from core review logic.

---

## C. Enterprise Readiness

* [x] SSO (OIDC / SAML)
* [ ] Multi-tenant architecture support
* [ ] Per-organization configuration
* [ ] API key management
* [ ] Add notifications integrations (Slack, Microsoft Teams, email/webhooks)
* [x] Export/import full project bundle
* [x] Backup/restore functionality

---

## D. Platform Stability & Trust

For open source credibility:

* [ ] Health endpoint
* [ ] Full E2E test coverage for:

  * Create â†’ Edit â†’ Review â†’ Approve â†’ Sign â†’ Archive
* [ ] Deterministic migrations
* [x] Seed demo data (for open source demo mode)
* [ ] Docker Compose dev stack
* [x] Production deployment guide

---

# UX Clarity Improvements

You wrote:

> Ensure Project view allows place for reviewers to add comments

I would rewrite that as:

* [x] Add embedded reviewer discussion panel within Project View, supporting threaded comments, tagging, and disposition tracking.

More precise. Product-focused.

---

# One More Thing Youâ€™re Missing

This is important:

## Document Version Lineage

* [ ] Automatic version incrementing
* [ ] Branch/merge support (parallel review tracks)
* [ ] Visual version history timeline
* [ ] Restore prior versions
* [ ] Freeze version at approval stage

Without strong versioning, review systems become fragile.

---

# If I Had To Prioritize (Pre-Release)

If your release window is 1â€“2 months, I would prioritize:

1. Workflow clarity + phase gating
2. Reviewer comments + disposition tracking
3. Dashboard restoration
4. Signature abstraction layer
5. Audit logging
6. E2E test hardening

Templates and AI enhancements can follow.

---

# Bigger Strategic Question

DocReview360 can become:

* A clean open-source document workflow engine
  OR
* A compliance-focused regulatory review platform
  OR
* A hybrid AI-augmented structured authoring system

Your roadmap starts to shape which direction youâ€™re going.



**1) Scope And Release Targets**
- [ ] Decide release artifacts: PyPI package, Docker image, GitHub release, docs site (yes/no for each).
- [ ] Decide support scope: CLI only vs full stack (API + frontend + workers).
- [ ] Define supported platforms (Python versions, OSes, Node versions) and document them.
- [ ] Freeze feature scope (no new features after this checkpoint; fixes only).
- [ ] Create a release branch (for example `release/v0.1.x`) and protect `main`.

**2) Repository Hygiene And Public Readiness**
- [ ] Run secret scan on the full history and working tree (gitleaks/trufflehog) and remediate anything found.
- [x] Verify `.env.example` contains only safe placeholders.
- [ ] Remove or rotate any hardcoded tokens, test credentials, or sample secrets.
- [ ] Remove unnecessary files and stale artifacts before release (temporary backups, local DB files, debug dumps).
- [ ] Confirm licensing intent: GPL-3.0-only is correct for all code and bundled assets.
- [x] Verify third-party licenses for frontend/vendor assets and data files (document in `docs/licenses.md` if needed).
- [ ] Ensure all â€œexample.comâ€ and placeholder URLs/emails are updated to real public addresses.
- [x] Fix README encoding issues (the current file has mojibake) so PyPI and GitHub render correctly.
- [x] Update README clone instructions (currently references another repo).
- [x] Reconcile `docreview360.yaml` vs `docreview360.yml` references in docs and CLI output.
- [ ] Confirm `SECURITY.md` contact email is real and monitored.

**3) Packaging And Versioning**
- [x] Confirm version alignment across `pyproject.toml` `[project]` and `[tool.poetry]`.
- [ ] Decide versioning scheme (SemVer) and document it in `CHANGELOG.md`.
- [x] Add a `CHANGELOG.md` following Keep a Changelog (required by `.dev/AGENTS.md`).
- [ ] Ensure `LICENSE` and `README.md` are included in the sdist and wheel metadata.
- [x] Add PyPI classifiers, keywords, and `project.urls` in `pyproject.toml`.
- [ ] Verify entry points: `docreview360` CLI works after install from a fresh venv.
- [ ] Build distribution artifacts: `python -m build` and validate with `twine check dist/*`.
- [ ] Test install from the built artifacts in a clean environment.
- [ ] (If publishing) Perform a TestPyPI dry run first.
- [ ] Decide whether frontend assets are part of the PyPI package (if yes, document build steps).

**4) Documentation And User Experience**
- [ ] Audit docs in `docs/` for broken links and outdated instructions.
- [ ] Ensure README structure matches `.dev/AGENTS.md` requirements (Install â†’ Quick-start â†’ Features â†’ Contributing â†’ License).
- [ ] Add/verify Quick Start that works on Windows and macOS/Linux.
- [ ] Update CLI docs (`docs/cli.md`) with latest commands and config file names.
- [ ] Publish architecture overview (`docs/adr/0001-core-architecture.md`) and ensure it is accurate.
- [ ] Generate API docs via FastAPI and link them in README.
- [ ] If using MkDocs, run `mkdocs build --strict` and fix any errors.

**5) Backend Quality Gates (Per `.dev/AGENTS.md`)**
- [x] `ruff check src tests`
- [ ] `pytest -q`
- [ ] `pytest -q --cov=src --cov-branch --cov-report=term --cov-fail-under=90`
- [ ] `mypy --strict src tests` (if type coverage is adequate)
- [ ] `mutmut run` (mutation testing gate)
- [ ] `trivy fs .` (container/file system vulnerability scan)
- [ ] `bandit -r src -lll --skip B101`
- [ ] `python scripts/run-pip-audit.py`

**6) Frontend Quality Gates**
- [x] `npm ci` in `frontend/`
- [x] `npm test -- --run` (Vitest)
- [x] `npm run build` to validate production build
- [x] `npm audit` (or documented alternative) and resolve critical issues

**7) Frontend-Backend Integration (Your Known Gap)**
- [ ] Run E2E smoke: `E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_smoke poetry run python scripts/run_e2e.py`
- [ ] Run E2E full: `E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_full poetry run python scripts/run_e2e.py`
- [ ] Manually verify the full flow on a clean environment:
- [ ] Login as admin (`alice`) and non-admin (`bob`) works from UI.
- [ ] Create project in UI â†’ backend persists â†’ refresh shows project.
- [ ] Upload a document â†’ backend stores â†’ UI can view/edit.
- [ ] Approval request flow updates status in UI.
- [ ] Export to PDF and Markdown from UI (or CLI) and verify output.
- [ ] Frontend uses `NEXT_PUBLIC_API_BASE` correctly with the backend URL.
- [ ] CORS settings allow the frontend origin (`DOCREVIEW360_ALLOW_ORIGINS`).
- [ ] Error handling surfaces backend failures in the UI (simulate backend down).

**8) CI/CD And Automation**
- [ ] Verify GitHub Actions CI passes on a clean run (`.github/workflows/ci.yml`).
- [ ] Ensure coverage threshold in CI matches the AGENTS release gate (CI currently uses 70).
- [ ] Confirm E2E smoke runs on every PR and E2E full runs on `main`.
- [ ] Confirm nightly workflow runs and uploads artifacts on failure.
- [ ] Decide if you want automated PyPI publish on tag and add a workflow if needed.

**9) Security And Compliance**
- [ ] Review `SECURITY_REVIEW.md` for any open items and close or document them.
- [ ] Validate security checks mentioned in `SECURITY.md` are actually run.
- [ ] Confirm password policy, secrets management, and encryption-at-rest docs are accurate.
- [ ] Verify OAuth/OIDC defaults and token lifetimes are reasonable for public use.
- [ ] Ensure audit log integrity checks are enabled and documented.

**10) Infrastructure And Deployment Readiness**
- [ ] Verify Docker build works end-to-end (`docker build` and `docker run`).
- [ ] Validate `docker-compose.yml` brings up all dependencies.
- [ ] Confirm `docs/deployment.md` matches current env vars and services.
- [ ] Validate `settings.yaml` defaults for production are safe (no dev/test defaults).
- [ ] Confirm DB migration strategy (if any) and document it.

**11) Code Review And Fix-It Loop (Codex CLI Focus)**
- [ ] Run targeted code review for backend (API, auth, storage, ML, integrations).
- [ ] Run targeted code review for frontend (auth flow, API client, editor, exports).
- [ ] Run targeted code review for CLI and scripts (edge cases, config loading).
- [ ] For optimization changes, document prompt intent and expected output behavior before implementation.
- [ ] For each optimization change, run targeted tests first, then optimize code, then rerun unit and impacted E2E tests.
- [ ] For each review: open issues, fix, re-run unit tests, re-run impacted E2E.
- [ ] Ensure any risky changes are covered by tests (add tests if not).

**12) Release Execution**
- [ ] Bump version in `pyproject.toml` and align any frontend versioning if needed.
- [x] Stamp build metadata for UI footer (version, build number, build date, and git commit hash) during release packaging.
- [ ] Update `CHANGELOG.md` with release notes and date.
- [ ] Tag the release in git (annotated tag).
- [ ] Create GitHub release with notes, assets, and checksums.
- [ ] Publish to PyPI (if chosen) after TestPyPI verification.
- [ ] Publish Docker image (if chosen) and verify `latest` and versioned tags.
- [ ] Announce release with upgrade notes and known issues.

**13) Post-Release Verification**
- [ ] Install from PyPI into a fresh venv and run `docreview360 --help`.
- [ ] Smoke test the CLI â†’ API â†’ UI flow using the released artifacts.
- [ ] Verify docs site or README links resolve correctly.
- [ ] Monitor issues and security reports for the first week.

**14) Data Model And Migration Discipline**
- [x] Define migration policy (tooling/version pinning and forward-only migrations).
- [x] Add migration rollback test in CI.
- [x] Verify demo seed data works on fresh DB and migrated DB.
- [x] Add schema compatibility test for upgrade path v0.0.x -> v0.1.
- [x] Document supported DB engines and versions.
- [x] Define SemVer rule for schema-breaking changes (MAJOR bump required).

**15) Performance Baseline**
- [x] Measure and record API container cold-start time.
- [x] Measure and record load time for a representative 50-page document.
- [x] Measure and record approval state-transition latency.
- [x] Run a minimal concurrency load test (10-25 simultaneous reviewers) and record results.
- [x] Document the v0.1 performance envelope in README.

**16) Logging And Observability Standardization**
- [x] Standardize production logs as structured JSON.
- [x] Enforce request correlation IDs end-to-end.
- [x] Standardize severity levels and error taxonomy.
- [x] Redact sensitive fields in logs by default.
- [x] Document a recommended monitoring stack and minimum alerts.

**17) Legal And Governance Layer**
- [x] Add `TERMS.md` (warranty/liability baseline).
- [x] Add `CONTRIBUTING.md` with contribution and governance model.
- [x] Add `CODE_OF_CONDUCT.md`.
- [x] Clarify product intent: regulated approval workflow support vs informational review.
- [x] Add disclaimer: not legal advice and no regulatory certification implied.

**18) Data Retention And Deletion Policy**
- [x] Define document retention and archival policy.
- [x] Define soft-delete vs hard-delete behavior.
- [x] Define audit-log immutability and retention policy.
- [x] Add explicit export-before-delete workflow.
- [x] Document GDPR-style delete request handling.

**19) Configuration Hardening**
- [x] Require explicit production mode flag (`DOCREVIEW360_ENV=production`).
- [x] Fail fast if production mode is used with dev/test secrets.
- [x] Disallow `DEBUG=True` in production.
- [x] Enforce HTTPS-only cookies in production mode.
- [x] Enforce secure-default CORS policy (deny-by-default plus explicit allowlist).

**20) API Contract Stability**
- [x] Add OpenAPI schema snapshot test in CI.
- [x] Version API routes (for example `/api/v1/`).
- [x] Add frontend-backend API contract tests.
- [x] Document backward-compatibility guarantees and deprecation policy.

**21) Disaster Recovery Simulation**
- [x] Run backup/restore simulation before release.
- [x] Verify projects, versions, and audit logs survive restore.
- [x] Document restore runbook with RTO/RPO assumptions.

**22) Approval Provenance Locking**
- [x] Freeze document hash at approval time.
- [x] Store content hash alongside each signature record.
- [x] Validate document hash before signature finalization.
- [x] Show warning when current document differs from approved version.

**23) Security Hardening Enhancements**
- [x] Add login endpoint rate limiting.
- [x] Add brute-force protection policy (lockout/backoff).
- [x] Configure session expiration and idle timeout defaults.
- [x] Verify CSRF protection and tests for state-changing routes.
- [x] Document dependency pinning and update strategy.
- [x] Generate SBOM (CycloneDX) for each release artifact set.

**24) Packaging And Supply Chain Integrity**
- [x] Sign release tags (GPG or Sigstore) and verify signatures.
- [x] Add OCI metadata labels (`org.opencontainers.image.*`) to Docker images.
- [x] Publish container image digests in release notes.

**25) Test Determinism**
- [x] Remove time-based flakiness and freeze timestamps where needed.
- [x] Ensure tests pass in UTC and local time zones.
- [x] Remove implicit dependency on local machine state.

**26) Release Positioning And Design Principles**
- [x] Add a release positioning statement in README for v0.1 scope and non-goals.
- [x] Add a README "Design Principles" section:
- [x] Deterministic workflow enforcement.
- [x] Immutable audit trail.
- [x] Explicit role boundaries.
- [x] Version lineage transparency.
- [x] Optional AI assistance, never mandatory.
- [x] Compliance-friendly architecture.

---

**27) Phases & Document Types — Migrate From JSON Files to Database (Enterprise Scalability)**

Context: `phases.py` and `doc_types.py` currently use flat JSON files (`phases.json`,
`document_types.json`, `phase_workflow_links.json`) with `FileLock` for persistence.
This architecture is **not safe for production**: FileLock only works on a single
filesystem, so any multi-node deployment (load balancer, Kubernetes, Docker Swarm) will
cause nodes to diverge silently. Additionally, `models.py` already defines a
`DocumentType` SQLAlchemy table that is unused, and there is no `Phase` table at all.
The JSON files must be replaced with proper database-backed persistence.

**27a — Database Schema**
- [ ] Add `Phase` model to `src/docreview360/models.py`:
  - Columns: `id` (int PK), `name` (str, unique, indexed), `display_order` (int, default 0).
- [ ] Add `PhaseWorkflowLink` model to `src/docreview360/models.py`:
  - Columns: `id` (int PK), `phase_id` (FK → phases.id, unique), `workflow_template_id` (str).
- [ ] Verify the existing `DocumentType` model (`id`, `name`) in `models.py` has everything
  needed; add `display_order` column if missing for consistent ordering.
- [ ] Write an Alembic migration (`migrations/versions/`) that:
  - Creates the `phases` table.
  - Creates the `phase_workflow_links` table.
  - Seeds the nine default phases from the current `_bootstrap_sample()` list in the
    correct display order.
  - Is forward-only (no downgrade required, but document that).
- [ ] Verify the migration runs cleanly on a fresh DB and on a migrated existing DB.

**27b — Backend: Rewrite `phases.py`**
- [ ] Remove all in-memory list state (`_phases`, `_phase_workflow_links`), JSON read/write
  functions (`_load_phases_from_disk`, `_persist_phases`, etc.), and `FileLock` usage.
- [ ] Remove the `DOCREVIEW360_ENABLE_PHASE_PERSISTENCE` feature flag — persistence is now
  always-on via the DB.
- [ ] Remove `DATA_FILE` and `PHASE_WORKFLOW_LINKS_FILE` path constants.
- [ ] Rewrite public API functions to use SQLAlchemy sessions (`get_db()` from
  `database.py`):
  - `list_phases(db)` — query all Phase rows ordered by `display_order`.
  - `add_phase(db, name)` — insert a new Phase row; raise `ValueError` on duplicate.
  - `delete_phase(db, name)` — delete Phase row and its PhaseWorkflowLink; raise
    `KeyError` if not found.
  - `rename_phase(db, old, new)` — update Phase row name; raise `KeyError` if not found.
  - `get_phase_workflow_template(db, phase_name)` — join Phase + PhaseWorkflowLink.
  - `set_phase_workflow_template(db, phase_name, workflow_template_id)` — upsert
    PhaseWorkflowLink row.
  - `list_phase_workflow_links(db)` — return dict of phase name → workflow template id.
- [ ] Remove `reset_phases()` (or scope it to test-only with a clear comment).

**27c — Backend: Rewrite `doc_types.py`**
- [ ] Audit current `doc_types.py` for all in-memory state and JSON persistence logic;
  remove entirely.
- [ ] Align all public functions to use the existing `DocumentType` SQLAlchemy model:
  - `list_doc_types(db)` — query all DocumentType rows.
  - `add_doc_type(db, name)` — insert; raise `ValueError` on duplicate.
  - `delete_doc_type(db, name)` — delete; raise `KeyError` if not found.
  - `rename_doc_type(db, old, new)` — update name.
- [ ] Verify `DocumentType` rows referenced by `Template` have proper FK cascade behavior
  (restrict delete if templates reference the type, or document the policy).
- [ ] Remove `DOCREVIEW360_DOC_TYPES_FILE` env var and any related flags.

**27d — API Layer**
- [ ] Update all API route handlers in `api/__init__.py` that call `phases.py` or
  `doc_types.py` functions to inject the DB session via `Depends(get_db)` and pass it
  through.
- [ ] Remove the `document_types.json` file download endpoint (currently at line ~3273 in
  `api/__init__.py`) or replace it with a proper DB-backed export route if the export
  feature is needed.
- [ ] Confirm admin configuration menu CRUD routes for phases and doc types call the
  new DB-backed functions correctly.
- [ ] Confirm that adding, editing, or deleting a phase or doc type via the admin UI is
  immediately visible to all nodes (no cache or in-memory divergence).

**27e — Cleanup**
- [ ] Add `phases.json`, `document_types.json`, `phase_workflow_links.json`,
  `phases.json.lock`, `document_types.json.lock`, `phase_workflow_links.json.lock` to
  `.gitignore`.
- [ ] Delete any committed copies of `phases.json`, `document_types.json`, or
  `phase_workflow_links.json` from the repository.
- [ ] Remove `DOCREVIEW360_PHASES_FILE`, `DOCREVIEW360_DOC_TYPES_FILE`,
  `DOCREVIEW360_PHASE_WORKFLOW_LINKS_FILE`, and `DOCREVIEW360_ENABLE_PHASE_PERSISTENCE`
  from all docs, `.env.example`, and `e2e_runtime.py`.
- [ ] Remove `filelock` from dependencies if it is no longer used anywhere else; run
  `grep -r "filelock" src/` to confirm.

**27f — Tests**
- [ ] Delete or rewrite `tests/test_phase_persistence.py` — remove all file-mocking
  (`monkeypatch` on `DATA_FILE`) and replace with DB session fixtures.
- [ ] Delete or rewrite `tests/doc_types/test_doc_types_locking.py` — remove FileLock
  tests (no longer applicable).
- [ ] Delete or rewrite `tests/doc_types/test_persistence_flag.py` — persistence flag is
  gone.
- [ ] Add new integration tests that:
  - Verify phase CRUD survives a DB session close and reopen (true persistence).
  - Verify that two concurrent DB sessions see each other's writes (no stale in-memory
    state).
  - Verify deleting a phase also removes its PhaseWorkflowLink.
  - Verify deleting a doc type with referencing Templates is handled per the FK policy.
- [ ] Ensure all existing phase and doc type route tests still pass after the migration.
- [ ] Run full test suite and confirm coverage gate (90% branch) still passes.

**27g — Multi-Node / Deployment Verification**
- [ ] Confirm the app starts correctly with zero JSON files present (relies entirely on DB
  seed from migration).
- [ ] If deploying with Docker Compose or Kubernetes, verify that multiple API replicas
  all read/write the same phases from the shared database with no divergence.
- [ ] Update `docs/deployment.md` to remove any mention of JSON file volumes for phases
  or doc types.
- [ ] Update `docs/` architecture docs to reflect that phases and doc types are now
  database-backed like all other entities.











