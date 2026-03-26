# DocReview360 Release Checklist

This file tracks open work only.

When you finish an item, verify it, move any shipped summary to
`docs/latest_features.md` or `CHANGELOG.md`, and then delete the item here.

Target window: next month (confirm exact date and time zone).

## 1. Release blockers and execution

### Scope and branch control

- [ ] Freeze feature scope. Only fixes after this checkpoint.
- [ ] Create a release branch and protect `main`.
  Touch: git branch settings, GitHub branch protection.

### Repository hygiene and public readiness

- [ ] Decide whether `.dev/`, `.claude/`, and `CLAUDE.md` belong in the public repo.
- [ ] Review references to private repositories and mark them optional or remove
  them.
- [ ] Confirm public-repo settings are ready.
  Review: branch protection, issue tracker, security reporting, Actions
  permissions.

### Packaging and publish payload

- [ ] Test install from built artifacts in a clean environment.
- [ ] If publishing, run a TestPyPI dry run.

### Docs, verification, and CI

- [ ] Run `pytest -q --cov=src --cov-branch --cov-report=term --cov-fail-under=90`.
- [ ] Run `mypy --strict src tests` if strict typing is realistic now.
- [ ] Run `mutmut run`.
- [ ] Run `trivy fs .`.
- [ ] Run E2E smoke.
- [ ] Run E2E full.
- [ ] Manually verify the main flow on a clean environment.
  Cover: admin login, reviewer login, project creation, refresh persistence,
  document upload or view or edit, approval request flow, PDF or Markdown export,
  backend-unavailable UI handling.
- [ ] Verify GitHub Actions CI passes on a clean run.
- [ ] Decide whether PyPI publish should be automated on tag.

### Deployment readiness

- [ ] Verify the Docker build works end to end.
- [ ] Validate `docker-compose.yml` startup.
- [ ] Confirm `docs/deployment.md` matches the current services and env vars.
- [ ] Validate `settings.yaml` defaults are safe for production.

### Code review and controlled change loop

- [ ] Run targeted backend review.
- [ ] Run targeted frontend review.
- [ ] Run targeted CLI and scripts review.
- [ ] Document prompt intent and expected behavior before optimization changes.
- [ ] For each optimization change, run targeted tests first, then rerun unit and
  impacted E2E coverage.
- [ ] Open issues for review findings, fix them, and rerun relevant tests.
- [ ] Ensure risky changes are covered by tests.

### Optional automation experiments

- [ ] If `autoresearch` is evaluated, keep it report-only first and attach a
  fixed metric, budget, and pass or fail gate.
- [ ] Keep AI automation limited to repo quality work.
  Do not automate publishing, image pushes, or other external side effects
  without an explicit human step.
- [ ] Start with narrow surfaces only.
  Candidates: docs drift, packaging review, flaky test analysis, performance
  triage.

## 2. Product and UX backlog still open

### 34. Federal Style Validator cutover

- [ ] Remove `src/docreview360/regulatory.py` once the FSV proxy fully owns
  regulatory checks.
- [ ] Register the FSV TipTap plugin in `frontend/extensions/registry.ts`.
- [ ] Remove `frontend/extensions/tiptapFederalStyleLint.ts` after the FSV plugin
  is live.
- [ ] Align `frontend/pages/tools/checker.tsx` with the FSV visual system.
  Add screenshot or UI regression coverage when FSV design tokens are finalized.
- [ ] Confirm there is no remaining duplicate style, readability, or quality
  logic in DocReview360.
  Touch: `src/docreview360/api/tools_router.py`,
  `src/docreview360/regulatory.py`, `frontend/extensions/registry.ts`,
  `frontend/extensions/tiptapFederalStyleLint.ts`,
  `frontend/pages/tools/checker.tsx`.

### 50. iOS companion app backend readiness

**Phase 4: API ergonomics**

- [ ] Decide whether to add a compact rendered document-view endpoint for
  read-only mobile viewing.

**Phase 5: iOS planning outside this repo**

- [ ] Generate a Swift client from `/openapi.json`.
- [ ] Define Keychain storage for refresh tokens and PKCE verifiers.
- [ ] Plan offline-first sync and local cache behavior.
- [ ] Decide between `WKWebView` rendering and a native document viewer.
- [ ] Set up TestFlight and App Store Connect metadata.

### 51. 2026-03-25 admin, editor, and project UX review

**Project view, review flow, and approvals**

- [ ] Clarify or redesign the relationship between Reviewer Sign-off and
  Concurrence versus Approvals.
  The current distinction is not clear, the concurred date is missing where it
  should appear, and this may need either a combined experience or an
  administrator-selectable level of formality.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `src/docreview360/api/assignments_router.py`, `src/docreview360/api/approvals.py`,
  `src/docreview360/concurrence_gate.py`, help text or documentation.

## 3. Reliability hardening plan

### P2: Longer-term hardening

- [ ] R-15. Add property-based tests for models, crypto, and search behavior.
  Touch: `pyproject.toml`, `tests/property/`.

## 4. Final release sign-off

- [ ] All section 1 release-blocker items are complete.
- [ ] All P0 reliability items are complete.
- [ ] `pytest -q` passes in a clean environment.
- [ ] Critical end-to-end workflow is covered and passing.
  Flow: login -> create project -> upload document -> assign reviewer ->
  submit review -> sign -> close.
- [ ] Health endpoints return `200`.
  Verify: `/health/live`, `/health/ready`.
- [ ] Error responses follow the final `ErrorResponse` contract.
- [ ] Structured logging is verified in production-like logs.
- [ ] Rate limiting is verified with load or burst tests.
- [ ] CORS is verified against the production frontend origin.
- [ ] Secret-key rotation is tested.
- [ ] Backup and restore is tested end to end.
- [ ] Rollback steps are documented for DB migrations and containers.
- [ ] Version is bumped in `pyproject.toml`, and frontend versioning is aligned
  if needed.
- [ ] `CHANGELOG.md` is updated with release notes and date.
- [ ] Git tag is created.
- [ ] GitHub release is created with notes, assets, and checksums.
- [ ] PyPI publish is completed after TestPyPI verification, if publishing is
  enabled.
- [ ] Docker image publish is completed and tags are verified, if publishing is
  enabled.
- [ ] Release announcement and upgrade notes are drafted.

## 5. Post-release

- [ ] Install from PyPI into a fresh venv and run `docreview360 --help`.
- [ ] Smoke-test the CLI-to-API-to-UI flow using released artifacts.
- [ ] Verify docs site and README links resolve correctly.
- [ ] Monitor issues and security reports for the first week.
