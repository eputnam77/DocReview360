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

- [x] Finish starter-content wiring for new documents. Backend
  `GET /document-types/{name}/starter-content` is live, and
  `frontend/pages/editors/tiptap.tsx` now loads starter content first,
  falling back to `/templates` only on 404 or error. (2026-03-11)

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
- [x] Local "release shepherd" loop: `scripts/release-shepherd.sh` — reads checklist, picks first unchecked item, runs pytest, writes timestamped report to `artifacts/automation/`, lockfile prevents concurrent runs. (2026-03-11)
- [ ] Require artifact-based state for every autonomous run: prompt text, selected files, commands run, exit codes, test results, diff summary, and stop reason under `artifacts/automation/`.
- [ ] Define hard AI guardrails before any autonomous loop: approved model list, max turns, max tokens, retry limit, fallback model, writable path allowlist, and mandatory human review for high-risk files.
- [ ] Add a lockfile or lease so only 1 automation loop edits the repo at a time.
- [ ] Add a watchdog that stops the loop after repeated no-op diffs, repeated failing tests, or budget exhaustion.
- [ ] Prototype a Raspberry Pi-friendly runner for headless loops with a shell wrapper, lockfile, and append-only logs instead of relying on `cron` or `systemd`.
- [x] Custom Claude Code commands: `.claude/commands/triage-failure.md`, `docs-drift.md`, `checklist-next.md`, `packaging-audit.md`. (2026-03-11)
- [ ] Use Claude Code hooks to enforce "read tests first" and "run verification before write" for autonomous maintenance commands.
- [ ] Build a failing-test triage loop that watches `pytest`, Playwright, and E2E failures, clusters similar stack traces, drafts the likely root cause, and proposes the smallest patch.
- [ ] Build a flaky-test hunter that reruns smoke tests multiple times, captures artifacts, and ranks failures by frequency and first bad commit if git history is available.
- [x] Docs drift checker: `scripts/check-docs-drift.py` — checks version/port/env-var/Python-constraint consistency across README, docs/, pyproject.toml, Dockerfile. (2026-03-11)
- [ ] Build a packaging auditor that inspects wheel, sdist, and Docker contents and flags shipped tests, placeholders, internal files, or runtime junk before release.
- [x] Placeholder and metadata reviewer: `scripts/check-placeholders.py` — scans for example.com, TODO/FIXME, GPL refs, version mismatches across 1,252 files. (2026-03-11)
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

- [x] Finish migrating active frontend shared hooks, components, state, and utility code off `authenticatedFetch(\`${API}/...\`)` and raw `fetch(\`${API}/...\`)`. All 14 target files migrated to relative paths; `branding.ts` switched from raw `fetch` to `authenticatedFetch`. (2026-03-11)
- [x] Broaden the frontend raw-fetch guard: `scripts/check-api-fetch-pattern.mjs` scans all frontend source dirs; added `lint:api-fetch` to `package.json`. (2026-03-11)

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

- [x] Notification channel selection per reviewer preference. `UserNotificationPreference` model + `GET/PUT /notifications/preferences/me` and `/{username}` endpoints. `send_notification()` now routes via per-user channel. (2026-03-11)

**Phase 5 — Reviewer experience (what the reviewer sees)**

- [ ] Read-only document preview panel alongside the feedback table (deferred)

**Phase 6 — Project view layout and navigation**

- [ ] Collapsible document preview panel on the right side of Feedback/Signatures tabs (deferred)

**Phase 7 — Records retention and project close-out**

- [x] Wire NARA metadata to project API: `nara_schedule_number`, `nara_disposition_authority`, `nara_retention_period`, `nara_record_series` added to `ProjectModel` and `ProjectCreate`/`ProjectUpdate`. Returned in GET /projects/{id}. UI: "Records Retention (NARA)" collapsible card in Overview tab with 4 editable fields. `GET /projects/{id}/nara-metadata` endpoint added. (2026-03-11)

**Phase 8 — Deadline and SLA tracking**

- [x] Expose default review SLA configuration in the admin UI. `SLAPanel` component added to `document-types.tsx` with expandable per-doc-type SLA editor (review days, reminder days, escalation threshold) and "View All SLA Configurations" summary panel. (2026-03-11)

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
- [x] Keep the existing `useApprovals`, `useComments`, `useProjectReviewers`
  hooks but compose them under a new `useReviewCycle(projectId)` hook. Created
  `frontend/lib/useReviewCycle.ts` with full `ReviewCycleResult` interface. (2026-03-11)
- [x] Wire all review lifecycle state changes through the existing audit log
  (`log_event()`). 11 assignment + 4 feedback endpoints now emit audit events. (2026-03-11)
- [x] Wire all review lifecycle state changes through `emit_lifecycle_event()`.
  6 key lifecycle endpoints now emit webhook events. (2026-03-11)
- [x] E2E test: full review cycle (create project → assign reviewer → add feedback/question → SME answers → concurrence → sign → close → records package). `tests/test_item44_e2e_review_cycle.py`. (2026-03-11)
- [x] E2E test: reviewer replacement — Bob replaced by Charlie, Bob's feedback preserved in ledger. (2026-03-11)

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

- [x] Add `FEDERAL_STYLE_VALIDATOR_URL` config setting. Documented in `Config` dataclass. (2026-03-11)
- [x] Replace `POST /documents/preflight` style checks with conditional proxy to FSV when configured; falls back to internal. Response includes `"source": "fsv"|"internal"`. (2026-03-11)
- [x] Replace `POST /ai/regulatory-check` with conditional proxy to FSV when configured; falls back to internal. (2026-03-11)
- [x] Replace `POST /ml/quality` scoring with conditional proxy to FSV when configured; falls back to internal. Response includes `"source"` field. (2026-03-11)
- [ ] Remove `regulatory.py` duplicate pattern matching once FSV proxy is live.
- [x] Added `GET /fsv/status` endpoint: returns configured/reachable status with 2s health probe. (2026-03-11)

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

- [x] Add `last_quality_score`, `last_quality_date`, and `plain_language_grade` persistence to `Document` ORM and Pydantic model. (2026-03-11)
- [x] Compute and store scores on preflight runs: `POST /documents/preflight` calls `update_document_quality_score()` when `document_id` provided. (2026-03-11)
- [x] Add score history: `DocumentQualityScore` table + `GET /documents/{id}/quality-history` endpoint + `score_history` field in project scores response. (2026-03-11)
- [x] Include quality score summary in dashboard KPI cards. `avg_quality_score()` in reporting, `quality` KPI widget added to User/Manager/Admin dashboards with color-coded `Award` icon. (2026-03-11)

### 41) Editor, integrations, and content management

**Phase 1 — Enterprise content integrations**

- [x] Add Microsoft 365 co-authoring via WOPI. `wopi.py` module + `wopi_router.py` with CheckFileInfo, Lock/Unlock, GetFile/PutFile, discovery XML. `WOPILockRecord` ORM model. Registered in `api/__init__.py`. (2026-03-11)

**Phase 2 — Editor hardening**

- [x] Add offline editing support. `offlineStorage.ts` (IndexedDB + localStorage fallback), `useOfflineSync.ts` hook, offline/sync banners in TipTap editor, Hocuspocus disconnect/reconnect handlers, service worker stub. (2026-03-11)
- [x] Expand import/export format fidelity. Added RTF, ODT, EPUB, LaTeX input detection + extraction; Confluence wiki markup export; improved plain-text output. (2026-03-11)

**Phase 3 — Enterprise search and analytics**

- [x] Add OpenSearch/Elasticsearch stub: `search/_external.py` with `ExternalSearchClient`, `DOCREVIEW360_SEARCH_BACKEND`/`OPENSEARCH_URL`/`ELASTICSEARCH_URL` config vars. (2026-03-11)
- [x] Add analytics dashboard: `GET /dashboard/analytics` (manager/admin) + `GET /reports/analytics/export` (CSV/JSON). `analytics_dashboard()` in reporting module. (2026-03-11)

### 42) Configuration and extensibility

- [x] Add theme and white-label support. `primary_color`, `accent_color`, `sidebar_bg`, `sidebar_text` added to branding API + `GET /branding` response. Frontend `useTheme.ts` injects CSS custom properties; Sidebar uses `var(--sidebar-bg/text)`. Branding config page has color pickers. (2026-03-11)

### 45) Role-based dashboard UX improvements

Dashboards exist for User, Manager, and Admin roles with proper RBAC enforcement
and per-widget visibility customization. The following items improve discoverability
and role-appropriate navigation.

- [x] Add a **settings cog icon** to each dashboard header (User, Manager, Admin). Replaced text "Customize Dashboard" button with `<Settings>` cog icon button in all three dashboards. (2026-03-11)
- [x] Gate dashboard links in the sidebar by role. Sidebar now shows "Admin Dashboard" for admins, "Manager Dashboard" for managers, "My Dashboard" for all others. `roles` field added to `useUserStore`. (2026-03-11)
- [x] Persist widget visibility preferences to SQLite: `DashboardVisibilityRecord` ORM model; `dashboard_prefs.py` migrated to SQLite with settings_manager fallback; `VisibilityPayload` extended with `widgets: list[str]`; frontend dashboards now use `GET/PUT /dashboard/visibility` instead of localStorage. (2026-03-11)

### 46) Frontend localization readiness

Backend i18n infrastructure is complete (`i18n.py`, 70 keys, 4 locales, REST
endpoints). Frontend locale JSON files exist in `public/locales/`. Next.js i18n
routing is configured. However, **zero frontend components use the i18n system** —
all UI strings are hardcoded in English.

**Phase 1 — Hook and switcher**

- [x] Created `frontend/lib/useTranslation.ts` hook: loads from `GET /i18n/translations/{locale}`, React Query cache, nested key lookup (`t("nav.dashboard")`), `setLocale()`. (2026-03-11)
- [x] Created `frontend/components/LocaleSwitcher.tsx` dropdown with 4 locales (en/es/fr/de). Exported from `components/index.tsx`. (2026-03-11)
- [x] Store locale preference on backend: `locale` field in `update_preferences()`, `GET/PUT /users/me/locale` endpoints in `admin_router.py`. (2026-03-11)

**Phase 2 — String extraction and migration**

- [x] Extract hardcoded UI strings from `login.tsx`, `projects/index.tsx`, `dashboard/user.tsx`. `login.*`, `projects.*`, `dashboard.*` key sections added to all 4 locale JSON files. (2026-03-11)
- [x] Replace hardcoded strings with `t("key")` calls in `login.tsx`, `projects/index.tsx`, `dashboard/user.tsx`. (2026-03-11)
- [x] `LocaleSwitcher` added to sidebar footer. Translation keys added to all 4 locale files (`en`, `es`, `fr`, `de`). (2026-03-11)

**Phase 3 — Full coverage**

- [ ] Migrate remaining pages and components to use `useTranslation`.
- [x] Added `frontend/scripts/check-hardcoded-strings.mjs` lint script (`npm run lint:i18n`). Informational warnings only. (2026-03-11)
- [x] Branding/terminology overrides now applied on top of locale translations via `GET /i18n/terminology/{locale}?org_id=`. `useTranslation` accepts `{ orgId }` option. (2026-03-11)

### 47) In-app support and documentation

A "Support" link exists in the sidebar and the footer shows configurable
Support/Docs/Security/Privacy links via the branding system. However, the actual
help and documentation pages are stubs.

- [x] Replaced `/docs/` placeholder with real in-app help. `/help` page rebuilt with 5 tabs: Getting Started, Key Concepts, FAQ, Keyboard Shortcuts, API Reference. (2026-03-11)
- [x] `/help` page fleshed out with getting started guide, key concepts (Projects/Documents/Phases/Reviewers/Feedback), 7-item FAQ. (2026-03-11)
- [x] Sidebar "Support" link replaced with collapsible "Help & Support" section: Documentation, Getting Started, Keyboard Shortcuts, API Reference, About, Contact Support. (2026-03-11)
- [x] Added `HelpTooltip` component with popover. Tooltips added to: dashboard widgets (9 widgets in user.tsx), document-type config table headers and SLA panel fields, phase advancement gate button. (2026-03-11)
- [x] Wire `brandingSupportUrl` and `brandingDocsUrl`: sidebar Help & Support section uses branding store URLs as overrides for Documentation and Contact Support links. (2026-03-11)

### 48) Tool architecture cleanup and configuration persistence

The plugin marketplace and tool configuration system works but has architectural
gaps that affect reliability and simplicity.

**Tool state persistence**

- [x] Persist built-in plugin toggle state to SQLite via `BuiltinPluginStateRecord` ORM model. `get_builtin_status()` reads from DB; `set_builtin_plugin_state()` writes to DB + in-memory cache. Falls back to in-memory on DB error. (2026-03-11)
- [x] Add per-org tool configuration: `OrgToolConfig` ORM model + `GET/PUT /orgs/{org_id}/tools` and `GET/PUT /orgs/{org_id}/tools/builtin-status` endpoints. (2026-03-11)

**Grammar tool audit**

- [x] `language-tool-python`, `pylanguagetool`, and `pyspellchecker` moved to `"Community / Optional"` category with `is_community: True`. Non-community plugins sort first in `list_plugins_with_info()`. (2026-03-11)

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
- [x] Tools index page now shows Active/Disabled/Not-installed status badges, community labels, dimmed disabled cards, admin-only Configure links and Enable/Disable toggles for built-in plugins. (2026-03-11)
