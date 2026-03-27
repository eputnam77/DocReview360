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

- [ ] Decide whether frontend assets are part of the PyPI package and document
  the answer.
- [ ] Build a fresh wheel and sdist for inspection.
  Touch: `pyproject.toml`, `MANIFEST.in`.
- [ ] Verify the wheel and sdist contain only release artifacts.
  Include: `src/docreview360/**`, required templates, migrations, runtime JSON
  or schema assets, `README.md`, `LICENSE`.
  Exclude: runtime-generated state, logs, local databases, temp files.
- [ ] Test install from built artifacts in a clean environment.
- [ ] If publishing, run a TestPyPI dry run.

### Docs, verification, and CI

- [ ] Run `mkdocs build --strict` and fix errors.
  Touch: `mkdocs.yml`, `docs/`.
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

### 44. Review cycle and project view

- [ ] Add a read-only document preview beside the feedback table.
- [ ] Add a collapsible preview panel on the right side of the Feedback and
  Signatures tabs.
- [ ] Add or enable a TipTap comments extension that stores inline comments as
  anchored marks.
- [ ] Add or enable a TipTap track-changes or suggestions extension with reviewer
  attribution.
- [ ] On Submit Review, extract inline comments and suggestions from TipTap JSON
  into the backend feedback ledger with `source="inline"` and range anchors.
- [ ] Add a Jump to location action on inline feedback items so reviewers can
  reopen the anchored editor location.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `frontend/pages/projects/[id]/review.tsx`, review-cycle hooks, backend
  feedback endpoints, TipTap editor code.

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

**Dashboard and tools**

- [ ] Decide and implement the final tools information architecture.
  Recommendation: keep `Document Converter` as a standalone page, collapse the
  current `Federal Style Validator` and `Document Quality Checker` overlap into a
  single `Document Quality Checker` surface, and list `Federal Style Validator`
  as the first validation engine inside that page unless additional non-FSV
  checkers are actually added.
  Also decide whether a second checker such as Grammarly, Acrolinx, or an
  open-source grammar engine is planned before keeping multiple top-level
  quality-check entries.
  Touch: `frontend/pages/tools/index.tsx`, `frontend/pages/tools/document-quality.tsx`,
  `frontend/pages/tools/checker.tsx`,
  `frontend/pages/configuration/plugin-marketplace.tsx`, help or docs copy.

**Project view, review flow, and approvals**

- [ ] Clarify or redesign the relationship between Reviewer Sign-off and
  Concurrence versus Approvals.
  The current distinction is not clear, the concurred date is missing where it
  should appear, and this may need either a combined experience or an
  administrator-selectable level of formality.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `src/docreview360/api/assignments_router.py`, `src/docreview360/api/approvals.py`,
  `src/docreview360/concurrence_gate.py`, help text or documentation.
- [ ] Implement an actual approval action for assigned approvers.
  If an approval row exists for a user, that user must see a clear approve path
  such as Documenso, DocuSign, initials, or another configured method.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `src/docreview360/api/approvals.py`, `src/docreview360/approvals/signatures.py`,
  provider integration settings, approval-state regression tests.
- [ ] Redesign or repurpose Inline Document Comments so the feature has a clear
  purpose and does not duplicate Post Feedback.
  The current flow is confusing, returns `Document Not Found` in at least one
  path, and should either become true line-anchored document comments or be
  merged with the existing feedback model.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `frontend/pages/editors/tiptap.tsx`, `src/docreview360/api/comments_router.py`,
  document lookup or anchor resolution, inline-comment UX copy.

**Configuration and help**

- [ ] Redesign the administrator Configuration landing page to mirror the clearer
  flow and visual structure already used in Help and Support documentation.
  Keep the setup sequencing, but align the presentation for consistency.
  Touch: `frontend/pages/configuration/index.tsx`, shared layout components,
  relevant translation strings.
- [ ] Split or expand Help and Support documentation by role so administrator,
  project owner, reviewer, and approver tasks are not mixed together.
  If reviewer and approver documentation stays minimal, the UI itself must become
  explicit enough that those users do not need a separate guide.
  Touch: `frontend/pages/help.tsx`, help-content data structures, locale files,
  project or review UI guidance and empty-state copy.

## 3. Accessibility gate (required before release)

- [ ] Automated accessibility checks pass (axe-core, no critical violations).
  Run: `cd frontend && npm test -- --reporter=verbose 2>&1 | grep -E "a11y|accessibility"`.
- [ ] Manual AT test script completed for critical flows (login, project creation, review workflow, approvals, editor).
  AT combinations required: NVDA + Chrome, VoiceOver + Safari (keyboard-only).
- [ ] No unresolved WCAG 2.1 AA blockers in `docs/section508_wcag.md` conformance table.
- [ ] Skip-to-main-content link is verified functional in a real browser.
- [ ] Tab keyboard navigation (ArrowLeft/Right/Home/End) verified on all tab groups.

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
