# DocReview360 Release Checklist (Open Items Only)

This file tracks unfinished work only.

Completed work moved to:

- `docs/latest_features.md`

Target window: next month (confirm exact date and time zone).

## Release blockers and execution

### Template and authoring gaps

The verified workflow-template dropdown fix, `default_workflow_template_id`
rename, and curated starter templates were moved to `docs/latest_features.md`
on 2026-03-11.

- [ ] Finish starter-content wiring for new documents. Backend
  `GET /document-types/{name}/starter-content` is live, but
  `frontend/pages/editors/tiptap.tsx` still auto-applies `/templates`
  entries on blank documents instead of loading the curated starter-content
  endpoint.

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
- [ ] In-app support and documentation tasks are tracked in item 47.

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

Remaining open work after the 2026-03-11 verification is listed below.

The reviewer assignment, feedback, signature, lifecycle, records, and SLA work
verified on 2026-03-11 was moved to `docs/latest_features.md`.

**Phase 2 — Multi-channel notification for review events**

- [ ] Notification channel selection per reviewer preference (uses global settings for now)

**Phase 5 — Reviewer experience (what the reviewer sees)**

- [ ] Read-only document preview panel alongside the feedback table (deferred)

**Phase 6 — Project view layout and navigation**

- [ ] Collapsible document preview panel on the right side of Feedback/Signatures tabs (deferred)

**Phase 7 — Records retention and project close-out**

- [ ] Wire to existing NARA metadata: when the SME creates or edits a project,
  allow setting the NARA schedule number, disposition authority, retention
  period, and record series — pull from `nara_metadata.py` and surface in
  the project Overview tab (NARA fields in records package, UI wire-up deferred)

**Phase 8 — Deadline and SLA tracking**

- [ ] Expose default review SLA configuration in the admin UI. Backend
  `/document-types/{doc_type}/sla` and `/document-types/sla/all` endpoints
  exist, but `frontend/pages/configuration/document-types.tsx` does not
  surface those settings yet.

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

**Phase 3 — UX consistency and on-save validation**

The FSV experience must be identical whether running standalone in a browser or
inside DocReview360 under Tools. This establishes a consistent brand.

- [ ] Ensure the `/tools/checker` page renders FSV results using the same visual
  layout, color scheme, and severity icons as the standalone FSV browser app.
  Share CSS/design tokens or use FSV's component library if available.
- [ ] Add on-save validation: when a user saves a document in the TipTap editor,
  automatically trigger an FSV validation pass via the proxy endpoint. Store
  the result summary (score, issue count, top issues) on the document record.
- [ ] Display minimal FSV feedback in the **Project View** after on-save
  validation: a quality badge (green/amber/red) and issue count next to each
  document in the document list. Clicking the badge navigates to the full
  FSV results.
- [ ] Make on-save validation configurable: admin toggle to enable/disable
  auto-validation, and a per-document-type setting to skip validation for
  types where FSV checks do not apply.

**Phase 4 — Core Tool Pack designation**

FSV is the Core Tool Pack for DocReview360 — enabled by default for all orgs.

- [ ] Designate FSV as the "Core" tool in the plugin marketplace. Show it with a
  "Core" badge and place it first in the tools list.
- [ ] Ensure administrators can still disable FSV in Configuration → Tools if it
  does not apply to their organization (e.g., non-Federal use cases).
- [ ] When FSV is disabled, hide FSV-specific UI elements (quality badges in
  project view, FSV results cards in checker, TipTap lint decorations) but
  keep the document converter and other non-FSV tools available.

**Phase 5 — Full cutover and documentation**

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

### 45) Role-based dashboard UX improvements

Dashboards exist for User, Manager, and Admin roles with proper RBAC enforcement
and per-widget visibility customization. The following items improve discoverability
and role-appropriate navigation.

- [ ] Add a **settings cog icon** to each dashboard header (User, Manager, Admin)
  that opens the widget visibility picker modal. Replace or supplement the current
  text "Customize Dashboard" button with the cog for a more standard UX.
- [ ] Gate dashboard links in the sidebar by role. Currently the sidebar shows a
  single "Dashboard" link for all users. Show role-appropriate dashboard links
  (e.g., admin users see Admin Dashboard, managers see Manager Dashboard) or
  auto-redirect `/dashboard` to the highest-privilege dashboard for the user's role.
- [ ] Persist widget visibility preferences to the database instead of localStorage
  so preferences survive browser changes. The backend `GET/PUT /dashboard/visibility`
  endpoints exist but are backed by `settings.yaml` — migrate to the user record or
  a dedicated preferences table.

### 46) Frontend localization readiness

Backend i18n infrastructure is complete (`i18n.py`, 70 keys, 4 locales, REST
endpoints). Frontend locale JSON files exist in `public/locales/`. Next.js i18n
routing is configured. However, **zero frontend components use the i18n system** —
all UI strings are hardcoded in English.

**Phase 1 — Hook and switcher**

- [ ] Create a `useTranslation(namespace?)` React hook that loads translations
  from the backend `GET /i18n/translations/{locale}` endpoint (or from the static
  JSON files in `public/locales/`) and caches them via React Query.
- [ ] Add a locale switcher component (dropdown in the sidebar footer or user
  profile menu) that sets the active locale and triggers re-render.
- [ ] Store the user's locale preference on the backend (user record or
  settings) so it persists across sessions.

**Phase 2 — String extraction and migration**

- [ ] Extract hardcoded UI strings from high-traffic pages first:
  `login.tsx`, `projects/index.tsx`, `dashboard/user.tsx`,
  `dashboard/manager.tsx`, `dashboard/admin.tsx`.
- [ ] Replace hardcoded strings with `t("key")` calls using the
  `useTranslation` hook.
- [ ] Add missing translation keys to all four locale JSON files
  (`en`, `es`, `fr`, `de`).

**Phase 3 — Full coverage**

- [ ] Migrate remaining pages and components to use `useTranslation`.
- [ ] Add a CI check or lint rule that flags new hardcoded user-facing strings
  in `.tsx` files.
- [ ] Ensure the branding/terminology system (`branding.py`) overrides are
  applied on top of locale translations — org-specific terms like
  "Project" → "Case" must work in all locales.

### 47) In-app support and documentation

A "Support" link exists in the sidebar and the footer shows configurable
Support/Docs/Security/Privacy links via the branding system. However, the actual
help and documentation pages are stubs.

- [ ] Replace the `/docs/` iframe placeholder (`example.com`) with real in-app
  documentation. Options: render `docs/*.md` files server-side via the existing
  `GET /help` pattern, or build a lightweight docs viewer page that fetches and
  renders Markdown from the `docs/` directory.
- [ ] Flesh out the `/help` page beyond the "coming soon" placeholder. Include
  at minimum: getting started guide, key concepts (projects, documents, phases,
  reviewers), and FAQ.
- [ ] Add a **Support menu** (dropdown or expandable section in the sidebar) with
  links to: Documentation, Getting Started, Keyboard Shortcuts, API Reference
  (link to FastAPI `/docs`), About, and Contact Support.
- [ ] Add contextual help tooltips or "?" icons on complex UI elements
  (dashboard widgets, tool configuration, phase advancement gates) that link
  to the relevant documentation section.
- [ ] Wire the `brandingSupportUrl` and `brandingDocsUrl` from the branding
  system so that orgs can point the Support menu to their own help desk or
  documentation portal.

### 48) Tool architecture cleanup and configuration persistence

The plugin marketplace and tool configuration system works but has architectural
gaps that affect reliability and simplicity.

**Tool state persistence**

- [ ] Persist built-in plugin toggle state (FedStyleValidator, SCDocBuilder) to
  SQLite instead of the current in-memory dict. The current implementation in
  `plugin_marketplace.py` resets all toggles to "enabled" on server restart.
- [ ] Add per-org tool configuration so different organizations can enable
  different tool sets.

**Grammar tool audit**

- [ ] Remove or relegate `language-tool-python`, `pyspellchecker`, and `gingerit`
  from the default plugin marketplace. Users already have browser-based grammar
  tools (Grammarly, Acrolinx, browser spellcheck). These server-side grammar
  packages add complexity without clear incremental value. If kept, move them to
  a "Community / Optional" category in the marketplace UI.

**Duplicate logic removal**

- [ ] Audit `doc_validation.py`, `document_checker.py`, and
  `tiptapFederalStyleLint.ts` for checks that duplicate FSV functionality
  (style rules, acronym validation, heading structure, plain language scoring).
  Track removal behind item 34 FSV integration milestones.
- [ ] Consolidate the three separate validation endpoints
  (`/documents/preflight`, `/ai/regulatory-check`, `/ml/quality`) into a single
  unified validation flow that calls FSV once and returns categorized results,
  rather than requiring the frontend to make three parallel requests.

**Tool configurability**

- [ ] Add per-check granularity for FSV rules in the admin Configuration → Tools
  page. Administrators should be able to disable specific check categories
  (e.g., disable passive voice detection but keep acronym validation) without
  disabling the entire tool.
- [ ] Ensure the tools index page (`/tools`) clearly communicates which tools
  are active, disabled, or require installation, with admin-only "Configure"
  links.
