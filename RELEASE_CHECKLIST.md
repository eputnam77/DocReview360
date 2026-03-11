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

- [ ] **Fix the dropdown bug.** Change the admin document-type UI to fetch from
  `GET /workflow-templates` instead of `GET /templates`, so the dropdown shows workflow
  templates that `_resolve_workflow_template()` can actually resolve. Rename the column
  header from "Default Template" to "Default Workflow" for clarity.
- [ ] **Rename `default_template_id` → `default_workflow_template_id`** on `DocumentType`
  (model, DB column, API schema, frontend interfaces) to eliminate the naming ambiguity
  between authoring templates and workflow templates.
- [ ] **Ship curated starter templates** for the built-in document types. Replace the
  current `<h1>{name}</h1>` placeholders (`doc_types/_registry.py:219`,
  `api/__init__.py:430`) with short but useful starter content — section headings,
  boilerplate paragraphs, and placeholder fields — for common types such as Advisory
  Circular, Memorandum, and Release Notes. Persist through the existing `/templates`
  admin flow so admins can customise them.
- [ ] **Pre-populate editor content on document creation.** When a user creates a new
  document, load the doc type's authoring template as the initial TipTap editor content.
  Wire: doc type → `template` field (or a new `default_authoring_template_id` FK) →
  document creation API → editor. Add a targeted test that verifies template content
  appears in the editor on first load.

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

- [ ] Replace the bare `reviewers: list[str]` on the project with a
  `ReviewAssignment` model: `id`, `project_id`, `reviewer` (username),
  `status` (invited | reviewing | feedback_submitted | concurred |
  non_concurred | signed | declined | replaced), `requested_at`,
  `started_at`, `completed_at`, `signed_at`, `signature_id`, `due_date`,
  `replaced_by` (FK to another ReviewAssignment, null if active),
  `replacement_reason`
- [ ] Add `GET /users/search?q={term}&limit=10` endpoint for typeahead user
  search — query against username, display name, email, and department from
  the auth user repository; return name, role, department, email; restrict
  to authenticated users
- [ ] Build a `<UserPicker />` component: typeahead search field, dropdown
  showing matching users with name + role + department, click to select;
  reuse wherever a user needs to be assigned (reviewer, SME, delegate)
- [ ] Add backend endpoints on `ReviewAssignment`:
  - `POST /projects/{id}/assignments` — create assignment (body: reviewer,
    due_date); status starts as "invited"; triggers notification
  - `GET /projects/{id}/assignments` — list all assignments including
    replaced ones (for history)
  - `PUT /projects/{id}/assignments/{aid}` — update due_date or other fields
  - `POST /projects/{id}/assignments/{aid}/start` — reviewer acknowledges;
    transitions to "reviewing"
  - `POST /projects/{id}/assignments/{aid}/submit` — reviewer marks feedback
    done; transitions to "feedback_submitted"
  - `POST /projects/{id}/assignments/{aid}/concur` — reviewer concurs
  - `POST /projects/{id}/assignments/{aid}/non-concur` — reviewer does not
    concur; requires `reason` in body
  - `POST /projects/{id}/assignments/{aid}/replace` — SME replaces reviewer;
    body: `{ replacement_reviewer, reason }`; original assignment status →
    "replaced"; new assignment created for replacement reviewer
  - `DELETE /projects/{id}/assignments/{aid}` — remove (only if status is
    "invited" and no feedback submitted)
- [ ] Display reviewer table rows in the project view showing: user avatar /
  initials, display name, role, status badge (color-coded), due date,
  days remaining or overdue indicator, and available actions per status
- [ ] Show a reviewer progress summary at the top of the project view:
  e.g. "2 of 4 reviewers signed" with a segmented progress bar colored
  by status (gray = invited, blue = reviewing, amber = feedback submitted,
  green = signed, red = non-concurred)
- [ ] Backward compatibility: on first access, migrate existing
  `reviewers: list[str]` to `ReviewAssignment` records with status "reviewing"

**Phase 2 — Multi-channel notification for review events**

- [ ] Wire `send_notification()` to review assignment lifecycle events:
  - `review.assigned` — reviewer receives notification with project name,
    document title, SME name, due date, and a direct link to the project view
  - `review.reminder` — approaching or past due date
  - `review.feedback_received` — SME notified when a reviewer submits feedback
  - `review.question_asked` — SME notified when a reviewer posts a question
  - `review.question_answered` — reviewer notified when SME responds
  - `review.concurrence_requested` — reviewer asked to concur/sign
  - `review.signed` — SME notified when a reviewer signs
  - `review.replaced` — original reviewer notified they have been replaced;
    replacement reviewer receives the assignment notification
  - `review.all_complete` — SME notified when all reviewers have signed
- [ ] Notification channel selection: use the reviewer's configured preference
  from `GET /notifications/settings` (already exists); fall back to email
- [ ] Include a direct deep link in every notification:
  `/projects/{id}#reviewers` or `/projects/{id}#feedback` depending on the
  action the recipient needs to take
- [ ] Add a notification log visible in the project History tab so the SME can
  see which notifications were sent, when, and to whom

**Phase 3 — Feedback ledger with conversation flow**

- [ ] Add a `source` field to `CommentModel`: `"feedback"` (from project view
  ledger), `"inline"` (future: from editor), `"review"` (from legacy review
  page) so the UI can distinguish origin
- [ ] Add a `feedback_type` field to `CommentModel`: `"comment"` (general
  observation), `"question"` (requires SME response before concurrence),
  `"suggestion"` (proposed change to the document), `"non_concurrence"`
  (substantive objection)
- [ ] Add an `assignment_id` FK on `CommentModel` linking each feedback item
  to the `ReviewAssignment` that created it — enables per-reviewer filtering
  and the concurrence gate
- [ ] Replace the current separate "Reviews" and "Comments" sections with a
  single **Feedback** tab containing a unified, sortable, filterable table
- [ ] Columns: reviewer, feedback type (icon + label), content (expandable),
  tag (legal / style / technical / policy), status (open | accepted |
  rejected | resolved), SME response (inline-expandable), timestamp
- [ ] Filters: by reviewer, by feedback type, by status, by tag, by phase
- [ ] Each row supports a **threaded conversation**: reviewer posts → SME
  replies → reviewer responds → ... until the item reaches a terminal status;
  each reply triggers the appropriate notification event from Phase 2
- [ ] Each row has inline disposition actions (SME / project owner only):
  - **Accept** — SME agrees; status → accepted
  - **Reject** — requires a written reason; status → rejected
  - **Resolve** — SME addressed the concern; status → resolved
  - **Reply** — adds a threaded response; status stays open until explicitly
    dispositioned
- [ ] For "question" type items: the reviewer can mark "satisfied" after
  reading the SME's answer, or escalate to "non_concurrence" if unsatisfied
- [ ] Show a feedback progress bar: "15 of 18 items addressed" with counts
  per status, updated in real time via React Query invalidation
- [ ] Phase-scoped feedback: each project phase (e.g. "public comment",
  "final issuance") has its own feedback ledger section; when a phase
  advances, the current phase's feedback is archived (read-only) and a new
  ledger section opens for the next phase; all phases remain visible and
  expandable in the Feedback tab so the full history is in one place

**Phase 4 — Reviewer sign-off and concurrence**

- [ ] Gate the "Request Concurrence / Signature" action per reviewer: all
  feedback items from that reviewer must be in a terminal status (accepted |
  rejected | resolved) and all "question" items must have an SME response
  before the reviewer can be asked to concur
- [ ] Concurrence options per reviewer (presented as clear buttons):
  - **Concur** — reviewer agrees with the document as revised; transitions
    assignment to "concurred"
  - **Concur with Comments** — reviewer agrees but attaches final notes
  - **Non-concur** — reviewer objects; requires written explanation; this
    creates a "non_concurrence" feedback item and blocks phase advancement
    until the SME dispositions it or the reviewer is replaced
- [ ] After concurrence, present signature options with clear UI affordance:
  - Full digital signature (Documenso / DocuSign) — opens provider flow
  - Initials (existing `sign-initials` endpoint) — modal with 2–5 char input
  - Internal acknowledgement (checkbox + timestamp) — for low-ceremony or
    internal-only reviews
- [ ] After signing, freeze the reviewer's row — show signed date, signature
  provider badge, certificate link, and "Verified" checkmark
- [ ] When all assigned reviewers have signed, surface a prominent
  "All Reviews Complete — Ready for Next Phase" banner with:
  - "Advance Phase" button (if more phases remain)
  - "Submit for Publication" button (if this is the final phase)
  - "Close Project" button (if no further action needed)

**Phase 5 — Reviewer experience (what the reviewer sees)**

- [ ] When a reviewer clicks the notification link, land them on the project
  view with a **focused reviewer banner** at the top: "You have been asked
  to review [Document Title] by [SME Name]. Due: [Date]." with clear
  call-to-action buttons: "Open Document" (opens TipTap) and "Add Feedback"
  (scrolls to the feedback form)
- [ ] Auto-transition the reviewer's assignment status from "invited" to
  "reviewing" when they first open the project view
- [ ] Show the reviewer only their own feedback items by default (with a
  toggle to see all reviewers' feedback for context)
- [ ] Provide a prominent "Submit Review" button that:
  1. Confirms the reviewer has finished adding feedback
  2. Transitions their assignment to "feedback_submitted"
  3. Notifies the SME
  4. Disables further feedback submission from this reviewer until the SME
     re-opens or requests additional review
- [ ] If the reviewer has open questions awaiting SME response, show a
  "Waiting for SME Response" status on their banner — they cannot submit
  their review or concur until their questions are answered
- [ ] Read-only document preview panel alongside the feedback table so the
  reviewer can reference the document without switching to the editor

**Phase 6 — Project view layout and navigation**

- [ ] Restructure the project view around the review lifecycle with a
  horizontal stepper or status bar at the top showing the current phase and
  review state: Assign Reviewers → Collect Feedback → Address Feedback →
  Collect Signatures → Closed / Submitted to Records
- [ ] Keep the current sticky tab navigation but rename to: **Overview** |
  **Reviewers** | **Feedback** | **Signatures** | **History**
- [ ] **Overview tab**: project metadata (doc type, SME, phase, dates),
  document link (opens TipTap editor), KPI summary cards (reviewers
  assigned, feedback items, items addressed, signatures collected, days in
  current phase), workflow phase timeline showing all phases with
  completion status
- [ ] **Reviewers tab**: reviewer assignment table built on `<UserPicker />`
  for adding; per-row actions: Request Review, Replace (for OOO), Remove,
  Send Reminder; status badges; due date with overdue highlighting;
  drag-to-reorder if review sequence matters; bulk actions: remind all,
  export reviewer list
- [ ] **Feedback tab**: the unified feedback ledger from Phase 3 with
  phase-scoped sections; includes the feedback submission form at the top
  for reviewers, and the disposition controls for the SME
- [ ] **Signatures tab**: per-reviewer concurrence and signature status;
  sign / remind / reset actions; signed-document download; verification
  status with hash check; LTV package link; overall signature summary
- [ ] **History tab**: existing audit timeline augmented with review lifecycle
  events (assignment created, notification sent, feedback submitted,
  concurrence given, signature collected, phase advanced, reviewer replaced)
- [ ] Add a collapsible **document preview panel** (read-only rendered HTML)
  on the right side of the Feedback and Signatures tabs so users do not
  have to switch to the editor to see document context
- [ ] Ensure the project view is the **single source of truth** for review
  status — a user should never need to open the editor, the review page,
  and the approval table separately to understand where a review stands

**Phase 7 — Records retention and project close-out**

- [ ] Add a project status lifecycle: `draft` → `in_review` → `reviewed` →
  `ready_for_publication` → `published` → `submitted_to_records` → `closed`
- [ ] "Ready for Publication" status: SME sets this after all reviewers have
  signed and all feedback is dispositioned; blocks further feedback
  submission; the document content is frozen
- [ ] "Published" status: SME records that the document was submitted for
  publication outside the tool (e.g. Federal Register); captures external
  reference number, publication date, and publication venue as metadata
- [ ] "Submit to Records" action on project close-out:
  - Generates a **complete review record package** containing:
    all document versions (with diffs between versions), the full feedback
    ledger with all dispositions and conversation threads, all reviewer
    assignments with status history, all signatures and certificates,
    all notifications sent (from the notification log), NARA metadata
    (from existing `nara_metadata.py`), project audit trail
  - Export formats: PDF bundle (human-readable), ZIP archive (structured
    files), JSON manifest (machine-readable for records management systems)
  - Attaches the package to the project record and marks it immutable
- [ ] Wire to existing NARA metadata: when the SME creates or edits a project,
  allow setting the NARA schedule number, disposition authority, retention
  period, and record series — pull from `nara_metadata.py` and surface in
  the project Overview tab
- [ ] Add a `GET /projects/{id}/records-package` endpoint that generates and
  returns the review record package on demand; include a content hash for
  integrity verification
- [ ] Add a "Records" section to the project Overview tab (visible after
  close-out) showing: retention schedule, disposition date, package
  download link, integrity hash, and submission status

**Phase 8 — Deadline and SLA tracking**

- [ ] Add configurable review deadline per assignment (set by SME when
  assigning; editable later)
- [ ] Add configurable default review SLA per document type or phase
  (admin setting) — used as the default due date when assigning reviewers
- [ ] Show deadline status in the reviewer table: green (on track),
  amber (due within 2 days), red (overdue), with days remaining or
  days overdue count
- [ ] Automated reminders: send a reminder notification at configurable
  intervals (e.g. 3 days before due, 1 day before due, on due date,
  daily after overdue) — wire to existing `send_notification()` and
  Celery beat scheduler
- [ ] Escalation path: if a reviewer is overdue by a configurable threshold,
  notify the SME and optionally a supervisor or admin — use existing
  `escalate_to` field on the approval model
- [ ] SLA summary on the Overview tab: "3 of 4 reviewers on track",
  "1 overdue by 3 days" — visible at a glance

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
