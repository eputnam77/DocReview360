# DocReview360 Release Checklist (First Public Release)

Target window: next month (confirm exact date and time zone).

Recommended v0.1 strategy:

✅ GitHub Release (required)
✅ PyPI (CLI-first distribution)
🔶 Docker (optional but recommended if full stack is core value)


**WANT TO ADD**
You’re at the stage where clarity + product positioning matter as much as features.

Given that you’re preparing DocReview360 for public release (and potentially positioning it as a serious document review platform, not just an internal tool), I’d refine your list into:

1. Clear feature objectives
2. Platform integrity safeguards
3. Workflow/UX improvements
4. Enterprise-readiness features
5. Competitive differentiators

Below is a cleaned-up and expanded version of your list — followed by additional strategic ideas.

---

# Refined + Clarified Feature Roadmap (DocReview360)

## 1. Authoring & Templates

* [ ] Implement structured document templates using TipTap (modular, version-controlled)
* [ ] Keep TipTap core unmodified (consume directly from upstream repo; extend via plugins only)
* [ ] Establish update-safe plugin architecture to allow future TipTap upgrades without breakage
* [ ] Ensure authoring tools persist cleanly to CMS (schema validation + version snapshots)
* [ ] Add template version history and change tracking
* [ ] Allow template locking per project phase

---

## 2. Configuration & Workflow Architecture

* [ ] Standardize Configuration/Phases schema to match Document Types schema
* [ ] Allow dynamic phase configuration per document type
* [ ] Enable workflow-driven approvals table (users added dynamically, not hardcoded)
* [ ] Redesign Project View:

  * Visual workflow timeline
  * Phase status indicators
  * Embedded approvals grid
  * Clean, minimal UI
* [ ] Add reviewer comment section directly in Project View
* [ ] Ensure phase gating logic (cannot advance without required approvals)

---

## 3. Review & Signature Layer

* [ ] Support Documenso as default e-signature provider
* [ ] Add DocuSign integration as optional enterprise connector
* [ ] Abstract signature provider behind provider interface (future-proofing)
* [ ] Log signature events into audit trail

---

## 4. Dashboard & Visibility

* [ ] Restore full dashboard view array (project status, overdue reviews, approval state)
* [ ] Add executive summary dashboard (for leadership view)
* [ ] Add reviewer workload dashboard
* [ ] Add document aging metrics
* [ ] Add SLA tracking per phase

---

## 5. Review Experience Enhancements

* [ ] Inline reviewer commenting (threaded)
* [ ] Structured comment tagging (legal, style, technical, policy, etc.)
* [ ] Reviewer disposition workflow (open → resolved → accepted → rejected)
* [ ] Comment export to Word (for legacy workflows)
* [ ] Redline comparison view (document version diff)

---

# Strategic Additions (High Impact)

Based on your broader ecosystem and FAA-heavy background, these could differentiate DocReview360 significantly.

---

## A. Audit & Compliance Engine

* [ ] Immutable audit log
* [ ] Phase-based audit snapshots
* [ ] Exportable audit package (PDF + JSON)
* [ ] Role-based permission matrix visualization
* [ ] Verification override logging (you already have RBAC structure — extend it)

This aligns well with federal compliance workflows.

---

## B. AI-Assisted Review (Optional Layer)

Given your ScriptCore and style validator background:

* [ ] AI style validation pass (toggleable)
* [ ] Acronym validation check
* [ ] Heading structure validation
* [ ] Plain language scoring
* [ ] Regulatory citation checker
* [ ] “Pre-flight” validation before phase advancement

Make this optional and clearly separated from core review logic.

---

## C. Enterprise Readiness

* [ ] SSO (OIDC / SAML)
* [ ] Multi-tenant architecture support
* [ ] Per-organization configuration
* [ ] API key management
* [ ] Export/import full project bundle
* [ ] Backup/restore functionality

---

## D. Platform Stability & Trust

For open source credibility:

* [ ] Health endpoint
* [ ] Full E2E test coverage for:

  * Create → Edit → Review → Approve → Sign → Archive
* [ ] Deterministic migrations
* [ ] Seed demo data (for open source demo mode)
* [ ] Docker Compose dev stack
* [ ] Production deployment guide

---

# UX Clarity Improvements

You wrote:

> Ensure Project view allows place for reviewers to add comments

I would rewrite that as:

* [ ] Add embedded reviewer discussion panel within Project View, supporting threaded comments, tagging, and disposition tracking.

More precise. Product-focused.

---

# One More Thing You’re Missing

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

If your release window is 1–2 months, I would prioritize:

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

Your roadmap starts to shape which direction you’re going.



**1) Scope And Release Targets**
- [ ] Decide release artifacts: PyPI package, Docker image, GitHub release, docs site (yes/no for each).
- [ ] Decide support scope: CLI only vs full stack (API + frontend + workers).
- [ ] Define supported platforms (Python versions, OSes, Node versions) and document them.
- [ ] Freeze feature scope (no new features after this checkpoint; fixes only).
- [ ] Create a release branch (for example `release/v0.1.x`) and protect `main`.

**2) Repository Hygiene And Public Readiness**
- [ ] Run secret scan on the full history and working tree (gitleaks/trufflehog) and remediate anything found.
- [ ] Verify `.env.example` contains only safe placeholders.
- [ ] Remove or rotate any hardcoded tokens, test credentials, or sample secrets.
- [ ] Confirm licensing intent: GPL-3.0-only is correct for all code and bundled assets.
- [ ] Verify third-party licenses for frontend/vendor assets and data files (document in `docs/licenses.md` if needed).
- [ ] Ensure all “example.com” and placeholder URLs/emails are updated to real public addresses.
- [ ] Fix README encoding issues (the current file has mojibake) so PyPI and GitHub render correctly.
- [ ] Update README clone instructions (currently references another repo).
- [ ] Reconcile `docreview360.yaml` vs `docreview360.yml` references in docs and CLI output.
- [ ] Confirm `SECURITY.md` contact email is real and monitored.

**3) Packaging And Versioning**
- [ ] Confirm version alignment across `pyproject.toml` `[project]` and `[tool.poetry]`.
- [ ] Decide versioning scheme (SemVer) and document it in `CHANGELOG.md`.
- [ ] Add a `CHANGELOG.md` following Keep a Changelog (required by `.dev/AGENTS.md`).
- [ ] Ensure `LICENSE` and `README.md` are included in the sdist and wheel metadata.
- [ ] Add PyPI classifiers, keywords, and `project.urls` in `pyproject.toml`.
- [ ] Verify entry points: `docreview360` CLI works after install from a fresh venv.
- [ ] Build distribution artifacts: `python -m build` and validate with `twine check dist/*`.
- [ ] Test install from the built artifacts in a clean environment.
- [ ] (If publishing) Perform a TestPyPI dry run first.
- [ ] Decide whether frontend assets are part of the PyPI package (if yes, document build steps).

**4) Documentation And User Experience**
- [ ] Audit docs in `docs/` for broken links and outdated instructions.
- [ ] Ensure README structure matches `.dev/AGENTS.md` requirements (Install → Quick-start → Features → Contributing → License).
- [ ] Add/verify Quick Start that works on Windows and macOS/Linux.
- [ ] Update CLI docs (`docs/cli.md`) with latest commands and config file names.
- [ ] Publish architecture overview (`docs/adr/0001-core-architecture.md`) and ensure it is accurate.
- [ ] Generate API docs via FastAPI and link them in README.
- [ ] If using MkDocs, run `mkdocs build --strict` and fix any errors.

**5) Backend Quality Gates (Per `.dev/AGENTS.md`)**
- [ ] `ruff check src tests`
- [ ] `pytest -q`
- [ ] `pytest -q --cov=src --cov-branch --cov-report=term --cov-fail-under=90`
- [ ] `mypy --strict src tests` (if type coverage is adequate)
- [ ] `mutmut run` (mutation testing gate)
- [ ] `trivy fs .` (container/file system vulnerability scan)
- [ ] `bandit -r src -lll --skip B101`
- [ ] `python scripts/run-pip-audit.py`

**6) Frontend Quality Gates**
- [ ] `npm ci` in `frontend/`
- [ ] `npm test -- --run` (Vitest)
- [ ] `npm run build` to validate production build
- [ ] `npm audit` (or documented alternative) and resolve critical issues

**7) Frontend-Backend Integration (Your Known Gap)**
- [ ] Run E2E smoke: `E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_smoke poetry run python scripts/run_e2e.py`
- [ ] Run E2E full: `E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_full poetry run python scripts/run_e2e.py`
- [ ] Manually verify the full flow on a clean environment:
- [ ] Login as admin (`alice`) and non-admin (`bob`) works from UI.
- [ ] Create project in UI → backend persists → refresh shows project.
- [ ] Upload a document → backend stores → UI can view/edit.
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
- [ ] For each review: open issues, fix, re-run unit tests, re-run impacted E2E.
- [ ] Ensure any risky changes are covered by tests (add tests if not).

**12) Release Execution**
- [ ] Bump version in `pyproject.toml` and align any frontend versioning if needed.
- [ ] Update `CHANGELOG.md` with release notes and date.
- [ ] Tag the release in git (annotated tag).
- [ ] Create GitHub release with notes, assets, and checksums.
- [ ] Publish to PyPI (if chosen) after TestPyPI verification.
- [ ] Publish Docker image (if chosen) and verify `latest` and versioned tags.
- [ ] Announce release with upgrade notes and known issues.

**13) Post-Release Verification**
- [ ] Install from PyPI into a fresh venv and run `docreview360 --help`.
- [ ] Smoke test the CLI → API → UI flow using the released artifacts.
- [ ] Verify docs site or README links resolve correctly.
- [ ] Monitor issues and security reports for the first week.
