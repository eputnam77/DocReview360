# DocReview360 Release Checklist

This file tracks open work only.

When you finish an item, verify it, move any shipped summary to
`docs/latest_features.md` or `CHANGELOG.md`, and then delete the item here.

Target window: next month (confirm exact date and time zone).

## 1. Release blockers and execution

### Review blockers found on 2026-03-25

- [x] Fix the `/token` login regression. `tests/test_token.py::test_jwt_token_flow`
  currently returns `401` for `POST /token`.
  Touch: `src/docreview360/api/auth_router.py`, `src/docreview360/auth/_core.py`,
  `src/docreview360/auth/_repository.py`, `tests/test_token.py`. (2026-03-25)
- [x] Fix pytest temp-directory setup so targeted suites can run reliably in this
  workspace.
  Touch: `tests/conftest.py`, `.tmp/`, local temp-dir handling.
  Blocked suites during this review: `tests/test_release_checklist_user_fixes.py`,
  `tests/test_dashboard.py`. (2026-03-25)

### Scope and branch control

- [ ] Freeze feature scope. Only fixes after this checkpoint.
- [ ] Create a release branch and protect `main`.
  Touch: git branch settings, GitHub branch protection.

### Repository hygiene and public readiness

- [ ] Run a secret scan across full history and working tree.
- [ ] Rotate or remove any hardcoded tokens, test credentials, or sample secrets.
- [ ] Remove local-only and stale release artifacts from the repo root, or move
  them out of the default branch.
  Review: `_debug_test.py`, `ai-notes.md`, `push-after-fix.ps1`, `tatus`,
  local `.db` files, ad hoc JSON stores, `.tmp/` outputs.
- [ ] Decide whether `.dev/`, `.claude/`, and `CLAUDE.md` belong in the public repo.
- [ ] Remove or untrack legacy frontend-generated files that should not ship.
  Review: `frontend/document_types.json`, `frontend/phases.json`,
  `frontend/phase_workflow_links.json`, `frontend/pages__backup_js_*`.
- [ ] Replace remaining placeholder or stale public metadata.
  Review: `src/docreview360.egg-info/PKG-INFO`, docs metadata,
  `info@example.com`, `registry.example.com`, contact info, license text.
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
- [ ] Tighten the Docker build context so local junk is not copied into images.
  Touch: `.dockerignore`, `Dockerfile`, release build context.

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
- [ ] Ensure the CI coverage threshold matches the release gate.
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

### 49. Frontend stability follow-up

- [ ] Close the remaining hook-ordering investigation for `useProject`,
  `useApprovals`, and `usePhases`.
  Exit criteria: either prove the current undefined-to-id hydration path is safe
  with regression coverage or simplify the hooks so the risk disappears.
- [ ] Add delayed-response coverage for loading-to-loaded transitions.
  Current source-level guards exist, but the full MSW-style async transition
  coverage is still missing.
  Touch: `frontend/lib/useProject.ts`, `frontend/lib/useApprovals.ts`,
  `frontend/lib/usePhases.ts`, `frontend/pages/projects/[id]/index.tsx`,
  `frontend/pages/_app.tsx`, `frontend/__tests__/hookLoadingStates.test.ts`.

### 50. iOS companion app backend readiness

**Phase 2: Pagination**

- [x] Add `skip` and `limit` pagination to `GET /projects`. (2026-03-25)
- [x] Add `skip` and `limit` pagination to `GET /projects/{id}/feedback`. (2026-03-25)
- [x] Add `skip` and `limit` pagination to `GET /projects/{id}/assignments`. (2026-03-25)
- [x] Add `skip` and `limit` pagination to `GET /projects/{id}/notification-log`. (2026-03-25)
- [x] Add `skip` and `limit` pagination to `GET /documents`. (2026-03-25)
- [x] Add `skip` and `limit` pagination to `GET /comments/{project_id}`. (2026-03-25)
- [x] Return shared pagination metadata in responses.
  Target shape: `{ items: [...], total: N, skip: 0, limit: 20 }`.
  Touch: `src/docreview360/api/projects_router.py`,
  `src/docreview360/api/feedback_router.py`,
  `src/docreview360/api/assignments_router.py`,
  `src/docreview360/api/documents_router.py`,
  `src/docreview360/api/comments_router.py`,
  `src/docreview360/api/notifications_router.py` or related response models. (2026-03-25)

**Phase 3: Push notifications**

- [x] Add device token registration endpoints.
  Target: `POST /devices/register`, `DELETE /devices/{token}`. (2026-03-25)
- [ ] Integrate APNs with token-based auth.
- [ ] Extend `send_notification()` to dispatch APNs alongside Slack, Teams,
  email, and webhook flows.
- [x] Add `GET /notifications/unread-count` for badge updates.
  Touch: `src/docreview360/notifications.py`,
  `src/docreview360/api/notifications_router.py`, auth or session storage,
  device-token persistence. (2026-03-25)

**Phase 4: API ergonomics**

- [x] Add `GET /assignments/me/summary`. (2026-03-25)
- [ ] Add `Content-Length` headers on download responses.
- [ ] Decide whether to add a compact rendered document-view endpoint for
  read-only mobile viewing.
- [ ] Add `X-RateLimit-Remaining` and `X-RateLimit-Reset` response headers.
  Touch: `src/docreview360/api/assignments_router.py`,
  `src/docreview360/api/documents_router.py`, rate-limit middleware or response
  helpers.

**Phase 5: iOS planning outside this repo**

- [ ] Generate a Swift client from `/openapi.json`.
- [ ] Define Keychain storage for refresh tokens and PKCE verifiers.
- [ ] Plan offline-first sync and local cache behavior.
- [ ] Decide between `WKWebView` rendering and a native document viewer.
- [ ] Set up TestFlight and App Store Connect metadata.

### 51. 2026-03-25 admin, editor, and project UX review

**Dashboard and tools**

- [ ] Replace generic audit event names in the admin dashboard feed with useful
  human-readable messages that explain who did what.
  Examples to improve over: `read`, `create_project`, `list_workflows_endpoint`.
  Prefer the richer audit message or context fields when available.
  Touch: `frontend/pages/dashboard/admin.tsx`, `frontend/components/AuditTimeline.tsx`,
  `src/docreview360/api/dashboards_router.py`, `src/docreview360/audit.py`.
- [ ] Fix "Recently Active Users" so it shows real user names from user
  management instead of role labels such as `SME` or `Front Line Manager`.
  Touch: `frontend/pages/dashboard/admin.tsx`,
  `frontend/pages/configuration/user-management.tsx`,
  `src/docreview360/api/dashboards_router.py`, user lookup or audit activity
  aggregation.
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
- [ ] Root-cause and stop the recurring `Failed to fetch` crash on the project
  details page so it does not regress every few days.
  Current failure path: `frontend/lib/api.ts` -> `pages/projects/[id]/index.tsx`.
  Touch: `frontend/lib/api.ts`, `frontend/pages/projects/[id]/index.tsx`,
  related project-detail API calls, regression coverage for network or auth base
  URL failures.

**TipTap editor**

- [ ] Fix the Tools and Extensions sidebar so the Validation Summary area remains
  scrollable and visible when content exceeds the viewport.
  Touch: `frontend/pages/editors/tiptap.tsx`, sidebar layout or overflow CSS.
- [ ] Fix the Tools and Extensions sidebar scroll behavior after toggling items
  such as Enable Validation or Heading Lock.
  The toggle interaction must not trap scroll or prevent access to lower items.
  Touch: `frontend/pages/editors/tiptap.tsx`, sidebar state handlers, overflow
  management, relevant editor layout styles.
- [ ] Fix the heading-format dropdown so applying `Heading 1` or `Heading 2`
  actually changes the selected text node type.
  Touch: `frontend/pages/editors/tiptap.tsx`, TipTap command wiring, extension
  registration, regression tests for heading transforms.
- [ ] Fix indent and unindent so they visibly update eligible content and rely on
  working TipTap commands rather than dead wrappers.
  Touch: `frontend/pages/editors/tiptap.tsx`, `frontend/lib/tiptapCommandUtils.ts`,
  indentation extension wiring, editor regression tests.
- [ ] Define and implement the Submit action in the TipTap editor.
  The current button appears to do nothing. Add the intended workflow action and
  immediate feedback such as a modal, toast, or routed confirmation showing what
  was submitted and to whom.
  Touch: `frontend/pages/editors/tiptap.tsx`, review submission flow, related API
  endpoints, user-facing status messaging.

**Project view, review flow, and approvals**

- [ ] Clarify or redesign the relationship between Reviewer Sign-off and
  Concurrence versus Approvals.
  The current distinction is not clear, the concurred date is missing where it
  should appear, and this may need either a combined experience or an
  administrator-selectable level of formality.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `src/docreview360/api/assignments_router.py`, `src/docreview360/api/approvals.py`,
  `src/docreview360/concurrence_gate.py`, help text or documentation.
- [ ] Fix the Approvals table layout and add a dedicated user-assignee column to
  the left of the role column.
  The legal record must show the actual person, such as `Bob`, plus the role,
  such as `Front Line Manager`, and the approval date.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `frontend/pages/configuration/workflows/*.tsx`, workflow role mapping, user
  picker integration, export or audit representations.
- [ ] Implement an actual approval action for assigned approvers.
  If an approval row exists for a user, that user must see a clear approve path
  such as Documenso, DocuSign, initials, or another configured method.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `src/docreview360/api/approvals.py`, `src/docreview360/approvals/signatures.py`,
  provider integration settings, approval-state regression tests.
- [ ] Fix `Open review workspace` from the project view so it clearly navigates
  or explains why it cannot.
  The current control appears to do nothing.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `frontend/pages/projects/[id]/review.tsx`, route or tab navigation state,
  reviewer workspace entry conditions.
- [ ] Fix comment reply persistence and rendering so replies remain attached to
  the original comment or feedback item after refresh.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `src/docreview360/comments.py`, `src/docreview360/api/comments_router.py`,
  comment thread serialization and UI rendering.
- [ ] Redesign or repurpose Inline Document Comments so the feature has a clear
  purpose and does not duplicate Post Feedback.
  The current flow is confusing, returns `Document Not Found` in at least one
  path, and should either become true line-anchored document comments or be
  merged with the existing feedback model.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `frontend/pages/editors/tiptap.tsx`, `src/docreview360/api/comments_router.py`,
  document lookup or anchor resolution, inline-comment UX copy.
- [ ] Improve Audit History entries in project view so they show detailed,
  user-meaningful messages including who performed the action.
  Examples to improve over: `feedback.replied`, `feedback.submitted`.
  Touch: `frontend/pages/projects/[id]/index.tsx`, `frontend/components/AuditTimeline.tsx`,
  `src/docreview360/audit.py`, audit message serialization for project events.
- [ ] Fix audit-history timestamp display so the UI uses the expected local or
  user-facing timezone instead of showing apparently shifted times.
  Touch: `frontend/pages/projects/[id]/index.tsx`,
  `frontend/components/AuditTimeline.tsx`, date formatting helpers, backend
  timestamp serialization if needed.
- [ ] Fix new-project workflow selection so project creation uses the configured
  default workflow based on document type and phase without forcing users to edit
  the project afterward.
  Touch: `frontend/pages/projects/new.tsx`, `frontend/pages/projects/[id]/edit.tsx`,
  `frontend/pages/configuration/phases.tsx`,
  `frontend/pages/configuration/document-types.tsx`,
  `src/docreview360/api/__init__.py` or `src/docreview360/api/workflows_router.py`.

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

### User-requested follow-up

- [ ] Confirm `docreview360 init` is updated with the latest software
  applications.

## 3. Reliability hardening plan

This section keeps only the remaining work. WebSocket JWT auth is already in
place and was removed from this file.

### P0: Must finish before release

- [x] R-01. Introduce a unified error response contract.
  Touch: `src/docreview360/errors.py` (new),
  `src/docreview360/api/__init__.py`, routers incrementally.
  Exit criteria: shared `AppError` hierarchy, `ErrorResponse` model, stable
  4xx or 5xx envelope, `trace_id` included. (2026-03-25)
- [x] R-02. Fix test-suite ordering and environment leakage.
  Touch: `tests/conftest.py`, env-mutating tests, module-level caches.
  Exit criteria: full suite is order-independent and CI can catch pollution
  reliably. (2026-03-25)
- [x] R-03. Add dedicated integration coverage for untested routers.
  Add coverage for: admin, dashboards, organizations, SCIM, SLA, legal,
  records, branches, config, feedback, assignments, and WOPI.
  Touch: `tests/api/` new files. (2026-03-25)
- [x] R-04. Add startup configuration validation.
  Touch: `src/docreview360/config_validator.py` (new),
  `src/docreview360/api/__init__.py`. (2026-03-25)
- [x] R-05. Add global exception handling for unhandled errors and validation
  failures.
  Touch: `src/docreview360/api/__init__.py`.
  Note: implement this together with R-01 so the error envelope does not fork. (2026-03-25)

### P1: Strongly recommended before release

- [ ] R-06. Add systematic input validation constraints.
  Touch: router parameters and Pydantic models across `src/docreview360/api/`
  and domain `_models.py` files.
- [ ] R-07. Split oversized routers into focused modules.
  Targets: `src/docreview360/api/admin_router.py`,
  `src/docreview360/api/workflows_router.py`,
  `src/docreview360/api/tools_router.py`.
- [ ] R-08. Split `src/docreview360/models.py` into domain packages with
  backward-compatible re-exports.
- [ ] R-09. Break up `frontend/pages/projects/[id]/index.tsx` into smaller
  project components.
- [x] R-10. Replace the placeholder Dependabot config with real update rules for
  `pip`, `npm`, and `github-actions`.
  Touch: `.github/dependabot.yml`. (2026-03-25)
- [x] R-11. Standardize retry logic.
  Touch: `src/docreview360/retry.py` (new),
  `src/docreview360/event_dispatcher.py`,
  `src/docreview360/approvals/signatures.py`. (2026-03-25)
- [x] R-12. Add logging to silent catch blocks where failures should be
  diagnosable.
  Touch: `src/docreview360/notifications.py`, `src/docreview360/sod.py`,
  `src/docreview360/event_dispatcher.py`, other silent handlers. (2026-03-25)
- [x] R-13. Add typed response models to admin endpoints that still return raw
  dicts.
  Touch: `src/docreview360/api/schemas/admin_schemas.py` (new),
  `src/docreview360/api/admin_router.py`, other untyped routers. (2026-03-25)

### P2: Longer-term hardening

- [ ] R-14. Introduce a service layer for core business logic.
  Touch: `src/docreview360/services/` (new), routers incrementally.
- [ ] R-15. Add property-based tests for models, crypto, and search behavior.
  Touch: `pyproject.toml`, `tests/property/`.
- [x] R-16. Add per-module coverage reporting.
  Touch: `scripts/coverage-by-module.py` (new), `.github/workflows/ci.yml`. (2026-03-25)
- [ ] R-17. Remove the deprecated frontend API proxy once all consumers are
  migrated.
  Current remaining imports:
  `frontend/pages/api/document-types/[...slug].ts`,
  `frontend/pages/api/document-types/index.ts`,
  `frontend/pages/api/profile.ts`,
  `frontend/pages/api/phases.ts`,
  `frontend/pages/api/phases/[...slug].ts`.
  Touch: `frontend/lib/apiProxy.ts`, those API route files, and a lint guard to
  prevent reintroduction.
- [ ] R-18. Expose a Prometheus scrape endpoint.
  Touch: `src/docreview360/api/__init__.py`, `src/docreview360/monitoring.py`.
- [x] R-19. Add migration safety tooling and docs.
  Touch: `scripts/check-migration-safety.py` (new), `alembic/`,
  `.github/workflows/ci.yml`, `docs/migrations.md`. (2026-03-25)

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
