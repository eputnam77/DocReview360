# DocReview360 Release Checklist (Open Items Only)

This file tracks unfinished work only.

Completed work moved to:

- `docs/latest_features.md`

Target window: next month (confirm exact date and time zone).

## Release blockers and execution

### Template and authoring gaps

**Bug — admin dropdown populates from the wrong template list.**
The "Default Template" dropdown in `frontend/pages/configuration/document-types.tsx`
fetches from `GET /templates` (document-authoring templates from `template_manager.py`,
names like `"doc_type::Policy"`), but `default_template_id` on `DocumentType` is consumed
by `_resolve_workflow_template()` in both `api/__init__.py` and `projects_router.py`,
which checks against `workflow_templates` (names like `"branch-coordination"`). The two
namespaces never overlap, so the admin selection is silently ignored at project creation
and the fallback (`"branch-coordination"`) always wins.

- [x] **Fix the dropdown bug.** Changed `document-types.tsx` to fetch from
  `GET /workflow-templates`; column header renamed "Default Workflow". (2026-03-11)
- [x] **Rename `default_template_id` → `default_workflow_template_id`** on `DocumentType`
  (ORM attribute, Pydantic model, API schema, all frontend interfaces). DB column kept as
  `default_template_id` via `mapped_column(name=...)` for backward compat with existing
  data — a future Alembic migration can rename the physical column. (2026-03-11)
- [x] **Ship curated starter templates** for 10 built-in doc types (Advisory Circular,
  Memorandum, Policy, Order/Directive, SOP, Report, FAQ, Release Notes, User Guide,
  Guidance). `DEFAULT_DOC_TYPE_TEMPLATES` dict in `doc_types/_registry.py` replaces the
  bare `<h1>{name}</h1>` placeholder on bootstrap and reset. (2026-03-11)
- [x] **Pre-populate editor content on document creation.** `GET /document-types/{name}/starter-content`
  endpoint added to `tools_router.py`. Returns curated HTML from `doc_type.template`.
  Frontend editor can call this on first load. Targeted test in `test_item44_review_cycle.py`
  verifies curated content is served. (2026-03-11)

### 13) Scope and release targets

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

- [ ] Stop the Docker build from copying unnecessary repo content after dependency install,
  or verify `.dockerignore` fully protects the build context.

**Repository ignore list should be tightened before public release**

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

**43d) Frontend API migration is incomplete**

- [ ] Finish migrating active frontend shared hooks, components, state, and utility code off `authenticatedFetch(\`${API}/...\`)` and raw `fetch(\`${API}/...\`)`. Remaining active call sites include `frontend/lib/useApprovals.ts`, `frontend/lib/useProjects.ts`, `frontend/lib/useWorkflowInstance.ts`, `frontend/lib/useDocuments.ts`, `frontend/lib/useNotifications.ts`, `frontend/lib/useComments.ts`, `frontend/lib/useSessions.ts`, `frontend/lib/usePhases.ts`, `frontend/lib/useProject.ts`, `frontend/lib/useProjectReviewers.ts`, `frontend/lib/useReviewSummary.ts`, `frontend/components/ChatBot.tsx`, `frontend/utils/saveStatus.ts`, and `frontend/state/branding.ts`.
- [ ] Broaden the frontend raw-fetch guard so it checks active frontend source beyond `pages/` and fails on `authenticatedFetch(\`${API}/...\`)` as well as raw `fetch(\`${API}/...\`)` usage where relative authenticated paths are required.

## Product and architecture backlog

### 44) Document review cycle — project view redesign

This is the core user-facing workflow of the application. The project view must
guide an SME through: assign reviewers → collect feedback → address feedback →
collect signatures → close out / submit to records. Every piece of reviewer
feedback must be accounted for, dispositioned, and tied to a signature before
the review closes. The completed feedback ledger and all signatures become the
official review record for Federal records retention.

**Current state (gaps):**
- Reviewers are bare username strings with no lifecycle status or assignment flow
- No user search / picker — reviewers must be typed manually
- No "request review" action that notifies a reviewer and tracks their progress
- No unified feedback ledger where the SME dispositions every item
- No back-and-forth conversation flow where a reviewer can ask questions and
  withhold concurrence until the SME answers
- No link between "all feedback addressed" and "reviewer may now sign"
- No reviewer replacement flow for out-of-office scenarios
- No deadline / SLA tracking per reviewer assignment
- No records retention integration — completed reviews are not packaged for
  NARA submission despite `nara_metadata.py` existing
- Project view tabs (Details / Approvals / Reviews / History) do not tell a
  clear step-by-step review story
- Notification infrastructure exists (email, Slack, Teams, webhook via
  `send_notification()`) but is not wired to review assignment events

**Phase 1 — Reviewer lifecycle model and user picker**

- [x] `ReviewAssignment` SQLite-backed model in `review_assignments.py` + ORM in `models.py`:
  fields: id, project_id, reviewer, status (invited | reviewing | feedback_submitted |
  concurred | non_concurred | signed | declined | replaced), requested_at, started_at,
  completed_at, signed_at, signature_id, due_date, replaced_by, replacement_reason. (2026-03-11)
- [x] `GET /users/search?q={term}&limit=10` endpoint added to `auth_router.py`. Searches
  by username substring; returns username, display_name, active. (2026-03-11)
- [x] Build a `<UserPicker />` component (frontend, debounced typeahead using `GET /users/search`,
  keyboard navigation, inactive badge). In `frontend/components/UserPicker.tsx`. (2026-03-11)
- [x] Backend endpoints in `api/assignments_router.py` (registered in `api/__init__.py`):
  `POST/GET /projects/{id}/assignments`, `PUT /projects/{id}/assignments/{aid}`,
  `POST .../start`, `POST .../submit`, `POST .../concur`, `POST .../non-concur`,
  `POST .../replace`, `DELETE .../assignments/{aid}`. All transitions enforce
  reviewer-only actions and project-manage access for SME/admin. (2026-03-11)
- [x] Display reviewer assignment table with lifecycle status badges and progress summary bar in
  project view. "Reviewers" added to sticky NAV. `UserPicker` used for the invite form.
  Reminder bell button calls `POST .../remind`. (2026-03-11)
- [x] Show reviewer progress summary at the top of the reviewers section: "N / M reviewers
  complete" with color-coded progress bar. (2026-03-11)
- [x] Backward compatibility: `GET /projects/{id}/assignments` auto-migrates existing
  `reviewers: list[str]` to ReviewAssignment records with status "reviewing". (2026-03-11)

**Phase 2 — Multi-channel notification for review events**

- [x] Wire `send_notification()` to review assignment lifecycle events: `review.assigned`,
  `review.feedback_received`, `review.signed`, `review.replaced`, `review.non_concurred`,
  `review.all_complete` — all fire-and-forget via `_emit_review_notification()` in
  `assignments_router.py`. (2026-03-11)
- [x] `review.reminder` — `POST /projects/{id}/assignments/{aid}/remind` endpoint in
  `assignments_router.py`; fires `_emit_review_notification("review.reminder", …)` with deep link.
  Blocks on terminal status (409). (2026-03-11)
- [x] `review.question_asked` / `review.question_answered` — fired from `feedback_router.py` when
  a question-type item is created or when a non-reviewer replies to a question. (2026-03-11)
- [x] `review.concurrence_requested` — `POST /projects/{id}/assignments/{aid}/request-concurrence`
  endpoint in `assignments_router.py`; SME action that fires notification without changing status.
  `review.concurrence_requested` message added to `_emit_review_notification()`. (2026-03-11)
- [ ] Notification channel selection per reviewer preference (uses global settings for now)
- [x] Deep links in notifications — all `_emit_review_notification()` messages now include
  `/projects/{id}#reviewers` deep link. (2026-03-11)
- [x] Notification log (`notification_log.py`) — `log_notification()` persists every dispatched
  notification to SQLite; `GET /projects/{id}/notification-log` endpoint; History tab in project
  view renders a collapsible notification log table. (2026-03-11)

**Phase 3 — Feedback ledger with conversation flow**

- [x] Added `source` field to `CommentModel` ("feedback" | "inline" | "review"; default "inline").
  Constants: `COMMENT_SOURCES`. (2026-03-11)
- [x] Added `feedback_type` field to `CommentModel` ("comment" | "question" | "suggestion" |
  "non_concurrence"; default None). Constants: `COMMENT_FEEDBACK_TYPES`. (2026-03-11)
- [x] Added `assignment_id` FK field to `CommentModel` (optional, links to ReviewAssignment). (2026-03-11)
- [x] Backend: `feedback_ledger.py` — `FeedbackItem` SQLite-backed model; CRUD: create, list
  (with filters: reviewer/type/status/phase/assignment_id/parent_id), get, dispose
  (accept/reject/resolve), reply (threaded), mark_question_satisfied, get_feedback_progress.
  `api/feedback_router.py` registered in `api/__init__.py`. (2026-03-11)
  Endpoints: `GET/POST /projects/{id}/feedback`, `PUT .../feedback/{fid}/disposition`,
  `POST .../feedback/{fid}/reply`, `POST .../feedback/{fid}/question-satisfied`,
  `GET /projects/{id}/feedback/progress`.
- [x] "Reviews" and "Comments" sections replaced with a unified **Feedback** tab in
  project view (`frontend/pages/projects/[id]/index.tsx`). "Feedback" added to sticky NAV.
  Inline document comments moved to a collapsible "Inline Document Comments" sub-section. (2026-03-11)
- [x] Feedback tab columns: reviewer, feedback type (icon + label), content, status badge,
  timestamp, phase. Expandable thread view shows replies. (2026-03-11)
- [x] Filters by feedback type (comment/question/suggestion/non_concurrence/all) and status
  (open/accepted/rejected/resolved/all). (2026-03-11)
- [x] Threaded conversation: reply input per item; `POST .../reply` endpoint. `review.question_answered`
  fired when SME replies to a reviewer's question. (2026-03-11)
- [x] Inline disposition actions (SME/owner): Accept → accepted; Reject (with window.prompt for
  reason) → rejected; Resolve → resolved. (2026-03-11)
- [x] "Question" type items: reviewer can mark "satisfied" via `POST .../question-satisfied`. (2026-03-11)
- [x] Feedback progress bar: "N of M items addressed" with color-coded bar; counts by status;
  `GET /projects/{id}/feedback/progress` powers it via React Query. (2026-03-11)
- [x] Phase-scoped feedback ledger archive: `_update_workflow_phase()` in `projects_router.py` now
  calls `archive_phase_feedback(project_id, old_phase, archived_by=current_user.username)` when
  the phase advances, auto-resolving all open top-level feedback from the previous phase.
  Manual `POST /projects/{id}/feedback/archive-phase` endpoint also available. (2026-03-11)

**Phase 4 — Reviewer sign-off and concurrence**

- [x] Gate the "Request Concurrence / Signature" action per reviewer: eligibility check via
  `check_concurrence_eligibility()` in `concurrence_gate.py`; `GET .../eligibility` endpoint
  returns `eligible`, `open_items`, `unanswered_questions`. Frontend shows concur buttons only
  when `eligible=true`. (2026-03-11)
- [x] Concurrence options per reviewer (presented as clear buttons):
  - **Concur** — `POST .../concur`; transitions assignment to "concurred". (2026-03-11)
  - **Concur with Comments** — `POST .../concur-with-comments` with `{text}`; creates a
    `comment` feedback item and transitions to "concurred". (2026-03-11)
  - **Non-concur** — `POST .../non-concur` with `{reason}`; transitions to "non_concurred";
    SME notified. (2026-03-11)
- [x] After concurrence, present signature options:
  - Full digital signature (Documenso / DocuSign) — deferred (existing Approvals tab)
  - Internal acknowledgement — `POST .../sign-internal` with optional note; shown as "Internal
    Sign-off" button when eligible; stamps `signed_at`. (2026-03-11)
- [x] After signing, reviewer's row frozen — Signatures tab shows signed date with
  `CheckCircle2` icon; overdue highlighting on due date. (2026-03-11)
- [x] When all assigned reviewers have signed, "All Reviews Complete — Ready for Next Phase"
  banner with "Advance Phase" button (canEdit). Non-concurrence warning shown when applicable.
  `GET /projects/{id}/review-summary` drives this via `all_complete` field. (2026-03-11)

**Phase 5 — Reviewer experience (what the reviewer sees)**

- [x] When a reviewer clicks the notification link, land them on the project view with a
  **focused reviewer banner** at the top. Shows assignment status, due date, and CTA buttons:
  "Open Document" (TipTap link), "Submit Review", "Concur", "Concur with Comments", and
  "Internal Sign-off" (when eligible). (2026-03-11)
- [x] Auto-transition the reviewer's assignment status from "invited" to "reviewing" when they
  first open the project view — `POST /projects/{id}/assignments/view` called on mount, fires
  `review.started` notification. (2026-03-11)
- [x] Show the reviewer only their own feedback items by default — "My feedback only" toggle
  (checkbox) filters feedback items to `reviewer === username`. (2026-03-11)
- [x] "Submit Review" button — calls `POST .../submit`; transitions to `feedback_submitted`;
  notifies SME via `review.feedback_received`. Disabled when reviewer has unanswered questions.
  (2026-03-11)
- [x] "Waiting for SME Response" status on reviewer banner — full eligibility object stored;
  when `unanswered_questions > 0`, amber badge shown and Submit Review is disabled. (2026-03-11)
- [ ] Read-only document preview panel alongside the feedback table (deferred)

**Phase 6 — Project view layout and navigation**

- [x] Lifecycle stepper (`LifecycleStepper` component) at the top of the project view, driven
  by `GET /projects/{id}/review-summary` → `lifecycle_step`. Steps: Assign Reviewers →
  Collect Feedback → Address Feedback → Collect Signatures → Complete. (2026-03-11)
- [x] Sticky tab navigation renamed to: **Overview** | **Reviewers** | **Feedback** |
  **Signatures** | **Approvals** | **History**. (2026-03-11)
- [x] **Overview tab**: project metadata table, KPI cards, document quality scores, workflow
  timeline, overall progress bar, primary "Edit Document" CTA. (2026-03-11)
- [x] **Reviewers tab**: assignment table with `<UserPicker />` for invite form; status badges
  with color coding; due date; per-row reminder bell; bulk actions: "Remind All" button
  (reminders all non-terminal reviewers), "Export" button (downloads CSV). (2026-03-11)
- [x] **Feedback tab**: unified feedback ledger with progress bar, post-feedback form,
  type/status filter chips, "My feedback only" toggle, threaded items with disposition actions
  and inline reply, "Question satisfied" button. (2026-03-11)
- [x] **Signatures tab**: per-reviewer concurrence/sign-off cards with eligibility indicators,
  overdue highlighting, non-concurrence reason display; SME "Request Concurrence" and "Remind"
  buttons; reviewer "Concur", "Concur with Comments", "Internal Sign-off" buttons. (2026-03-11)
- [x] **History tab**: audit timeline enriched with synthetic review lifecycle events derived
  from assignment timestamps (invited, started, feedback submitted, concurred/signed); all
  events merged and sorted by timestamp descending. Notification log in collapsible sub-section.
  (2026-03-11)
- [ ] Collapsible document preview panel on the right side of Feedback/Signatures tabs (deferred)
- [x] Project view is single source of truth — lifecycle stepper, reviewer table, feedback
  ledger, signature status, and audit history all visible without leaving the project view.
  (2026-03-11)

**Phase 7 — Records retention and project close-out**

- [x] Add a project status lifecycle: `draft` → `in_review` → `reviewed` →
  `ready_for_publication` → `published` → `submitted_to_records` → `closed`
  (`project_lifecycle.py`, `VALID_TRANSITIONS` state machine, `is_feedback_blocked()`). (2026-03-11)
- [x] "Ready for Publication" status: SME sets this after all reviewers have
  signed and all feedback is dispositioned; blocks further feedback
  submission; the document content is frozen (`FEEDBACK_BLOCKED_STATUSES`,
  `GET /projects/{id}/lifecycle/feedback-blocked`). (2026-03-11)
- [x] "Published" status: SME records that the document was submitted for
  publication outside the tool (e.g. Federal Register); captures external
  reference number, publication date, and publication venue as metadata
  (`set_published_metadata()`, `PUT /projects/{id}/published-metadata`). (2026-03-11)
- [x] "Submit to Records" action on project close-out:
  - Generates a **complete review record package** (`records_package.py`):
    assignments, feedback ledger, notification log, NARA metadata, document
    versions; ZIP archive with SHA-256 integrity hash in `manifest.json`.
  - `GET /projects/{id}/records-package` returns ZIP with `X-Content-Hash` header.
  (2026-03-11)
- [ ] Wire to existing NARA metadata: when the SME creates or edits a project,
  allow setting the NARA schedule number, disposition authority, retention
  period, and record series — pull from `nara_metadata.py` and surface in
  the project Overview tab (NARA fields in records package, UI wire-up deferred)
- [x] Add a `GET /projects/{id}/records-package` endpoint that generates and
  returns the review record package on demand; include a content hash for
  integrity verification (`records_router.py`, `X-Content-Hash: sha256=...`). (2026-03-11)
- [x] Add a "Records" section to the project Overview tab (visible after
  close-out) showing: package download link, integrity hash, lifecycle status,
  and submission status (`frontend/pages/projects/[id]/index.tsx` Records section). (2026-03-11)

**Phase 8 — Deadline and SLA tracking**

- [x] Add configurable review deadline per assignment (set by SME when
  assigning; editable later) — `due_date` on `ReviewAssignment`, `PATCH .../assignments/{id}`. (2026-03-11)
- [x] Add configurable default review SLA per document type or phase
  (admin setting) — `sla_tracker.py`, `SLAConfig`, `sla_configs` SQLite table;
  `GET/PUT /document-types/{doc_type}/sla`, `GET /document-types/sla/all`. (2026-03-11)
- [x] Show deadline status in the reviewer table: green (on track),
  amber (due within 2 days), red (overdue), with days remaining or
  days overdue count (`get_deadline_status()`, color-coded in reviewer table,
  `GET /projects/{id}/sla-deadlines`). (2026-03-11)
- [x] Automated reminders: send a reminder notification at configurable
  intervals (e.g. 3 days before due, 1 day before due, on due date,
  daily after overdue) — `run_sla_reminders()` wired to `send_notification()`;
  Celery beat task `docreview360.sla_reminder_sweep` via `register_sla_beat_task()`;
  `POST /projects/{id}/run-sla-reminders`. (2026-03-11)
- [x] Escalation path: if a reviewer is overdue by a configurable threshold,
  notify the SME — `escalation_threshold_days` in `SLAConfig`; overdue notifications
  also logged to `notification_log`. (2026-03-11)
- [x] SLA summary on the Overview tab: "3 of 4 reviewers on track",
  "1 overdue by 3 days" — `SLASummary` model, `get_sla_summary()`,
  `GET /projects/{id}/sla-summary`; SLA summary card in Overview section. (2026-03-11)

**Future / optional — TipTap inline feedback extraction**

Not critical for the initial release if the project-view feedback ledger is
effective. Revisit after the core review cycle is solid.

- [ ] Add or enable a TipTap comments extension that stores inline comments
  as marks anchored to document ranges
- [ ] Add or enable a TipTap track-changes / suggestions extension with
  reviewer attribution
- [ ] On "Submit Review", extract inline comments and suggestions from the
  TipTap JSON and POST them to the backend feedback ledger with
  `source = "inline"` and a range anchor
- [ ] Add a "Jump to location" link on inline feedback items that opens
  the TipTap editor scrolled to the anchored range

**Implementation notes:**

- [ ] Migrate `frontend/pages/projects/[id]/review.tsx` functionality into
  the new Feedback tab; deprecate or redirect the standalone review page
- [ ] Keep the existing `useApprovals`, `useComments`, `useProjectReviewers`
  hooks but compose them under a new `useReviewCycle(projectId)` hook that
  combines reviewer assignment status, feedback progress, and signature
  state into a single query result for the project view
- [ ] Backend: add a `GET /projects/{id}/review-summary` endpoint that
  returns reviewer statuses, feedback counts by status, signature states,
  deadline alerts, and phase gate readiness in a single response to avoid
  multiple round trips on page load
- [ ] All new UI must work at the `ReviewAssignment` level, not bare
  usernames — ensure backward compatibility by migrating existing
  `reviewers: list[str]` data to `ReviewAssignment` records on first access
- [ ] Wire all review lifecycle state changes through the existing audit log
  (`log_event()`) so the History tab is automatically populated
- [ ] Wire all review lifecycle state changes through `emit_lifecycle_event()`
  so external webhook subscribers are notified
- [ ] Add E2E test covering the full cycle: create project → search and add
  reviewer via user picker → reviewer receives notification → reviewer opens
  project and adds feedback (comment + question) → SME answers question →
  SME accepts comment and resolves question → SME requests concurrence →
  reviewer concurs and signs → SME advances phase → SME closes project →
  records package is generated and downloadable
- [ ] Add E2E test for reviewer replacement: assign reviewer → reviewer is
  OOO → SME replaces with another user → replacement reviewer picks up
  where the original left off → original reviewer's submitted feedback is
  preserved in the ledger

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

### 40) Compliance, records management, and accessibility

- [x] Add long-term digital signature compliance support. — `integrations/signature/lts.py`: RFC 3161 TSA client, OCSP caching, CRL caching, `LTVPackage` (baseline/extended/archival), `create_ltv_package`, `serialize/deserialize_ltv_package`, `create_archive_timestamp`. `attach_lts_package` + `get_ltv_package` added to `approvals/signatures.py`. `GET /signatures/{id}/ltv` endpoint in `documents_router.py`. 52 tests in `tests/test_lts_compliance.py`.

### 41) Editor, integrations, and content management

**Phase 1 — Enterprise content integrations**

- [ ] Add Microsoft 365 co-authoring via WOPI.

**Phase 2 — Editor hardening**

- [ ] Add offline editing support.
- [ ] Expand import and export format fidelity.

**Phase 3 — Enterprise search and analytics**

- [ ] Add OpenSearch or Elasticsearch-backed full-text search.
- [ ] Add analytics dashboard and exportable reports.

### 42) Configuration and extensibility

- [ ] Add theme and white-label support.
