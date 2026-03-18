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
  `GET /document-types/{name}/starter-content` is live and covered by
  `tests/test_item44_review_cycle.py`, and `frontend/__tests__/starterContent.test.ts`
  now has executable frontend regression coverage again: `frontend/package.json`
  runs Vitest with `--configLoader runner`, avoiding the CommonJS config-loader
  path that triggered `ERR_REQUIRE_ESM` under Node `18.20.4`, and
  `npm test -- __tests__/starterContent.test.ts` passes. (Completed 2026-03-18)

### 13) Scope and release targets

- [x] Define supported platforms and document them. `docs/supported-platforms.md`
  now reflects the frontend Node toolchain requirement (`vite@7.x`: Node
  `^20.19.0 || >=22.12.0`) and marks older Node versions unsupported.
  (Completed 2026-03-17)
- [ ] Freeze feature scope. Fixes only after this checkpoint.
- [ ] Create a release branch and protect `main`.

### 14) Repository hygiene and public readiness

- [ ] Run a secret scan on the full history and working tree.
- [ ] Remove or rotate any hardcoded tokens, test credentials, or sample secrets.
- [ ] Remove unnecessary files and stale artifacts before release.
- [x] Ensure all `example.com` and placeholder URLs or emails are updated.
  Replaced the docs iframe placeholder URL and Helm maintainer placeholder email.
  (Completed 2026-03-17)

### 15) Packaging and versioning

- [ ] Test install from the built artifacts in a clean environment.
- [ ] If publishing, perform a TestPyPI dry run.
- [ ] Decide whether frontend assets are part of the PyPI package and document the answer.

### 15a) Publish payload and exclusion rules

**PyPI wheel and sdist must include only release artifacts**

- [ ] Ship only runtime Python package contents needed by installs:
  `src/docreview360/**`, required templates, migrations, runtime JSON or schema files,
  `README.md`, `LICENSE`, and package metadata.
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
  Frontend docs iframe and Helm maintainer placeholders were replaced on 2026-03-17;
  continue scanning for any remaining placeholder values.
- [ ] Update docs and metadata that still mention GPL or placeholder contact data.
  Missing requirement: stale generated metadata still remains in
  `src/docreview360.egg-info/PKG-INFO`, which still advertises
  `info@example.com`, `GPL-3.0-only`, and GPL classifiers. Remove or regenerate
  that stale metadata before moving this out. (2026-03-12 verification)
- [ ] Review references to private repositories and remove or clearly mark them as optional.
- [ ] Confirm branch protection, issue tracker settings, security reporting, and Actions
  settings are ready for a public repository.

### 16) Documentation and user experience

- [x] Ensure `README.md` matches `.dev/AGENTS.md` structure requirements.
  README setup instructions now align with Python 3.11-3.12 support and call
  out Python 3.12 as the recommended venv target. (Completed 2026-03-17)
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
- [ ] If `autoresearch` is trialed, start with read-only or report-only tasks first. Do not let it write code until its summaries are consistently useful on this repo.
- [ ] If `autoresearch` is trialed, restrict it to narrow surfaces such as docs drift, packaging review, flaky test analysis, or performance triage before attempting broader "improve the app" loops.

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

2026-03-18 verification note: the shared frontend Vitest startup blocker is
resolved. `frontend/package.json` now runs `vitest run --configLoader runner`,
and the cited frontend suites in this section pass under Node `18.20.4`.

- [x] Finish migrating active frontend shared hooks, components, state, and
  utility code off `authenticatedFetch(\`${API}/...\`)` and raw `fetch(\`${API}/...\`)`.
  Added `frontend/__tests__/brandingStore.test.ts` — 15 tests covering
  `state/branding.ts` end-to-end (source guard, fetch URL contract, store population,
  error fallback, idempotency). `npm test -- __tests__/brandingStore.test.ts`
  passes. (Completed 2026-03-18)
- [x] Broaden the frontend raw-fetch guard: `scripts/check-api-fetch-pattern.mjs`
  and `lint:api-fetch` exist. Added `frontend/__tests__/checkApiFetchPattern.test.ts`
  — 10 tests covering clean-pass, violation detection in all 5 scan dirs,
  login.tsx exemption, and relative-path allowance.
  `npm test -- __tests__/checkApiFetchPattern.test.ts` passes. (Completed 2026-03-18)

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

2026-03-18 verification note: the shared Vitest/Node blocker from item 43d is
resolved, and the cited review-cycle frontend suites below were rerun.

**Phase 2 — Multi-channel notification for review events**

The verified notification-preference work was moved to
`docs/latest_features.md` on 2026-03-12.

**Phase 5 — Reviewer experience (what the reviewer sees)**

- [ ] Read-only document preview panel alongside the feedback table (deferred)

**Phase 6 — Project view layout and navigation**

- [ ] Collapsible document preview panel on the right side of Feedback/Signatures tabs (deferred)

**Phase 7 — Records retention and project close-out**

- [x] Wire NARA metadata to project API: Added `frontend/__tests__/naraAndSlaPanel.test.ts`
  — source-level tests covering state declarations, API load from project data, save
  payload shape (4 fields + PUT), success/error toasts.
  `npm test -- __tests__/naraAndSlaPanel.test.ts` passes. (Completed 2026-03-18)

**Phase 8 — Deadline and SLA tracking**

- [x] Expose default review SLA configuration in the admin UI. SLA endpoints
  and query wiring covered in `frontend/__tests__/naraAndSlaPanel.test.ts`
  — 6 tests for sla-summary, sla-deadlines, run-sla-reminders, conditional render,
  and query key shape. `npm test -- __tests__/naraAndSlaPanel.test.ts` passes.
  (Completed 2026-03-18)

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

- [x] Migrate `frontend/pages/projects/[id]/review.tsx` functionality into
  the new Feedback tab. Added source guards in `frontend/__tests__/reviewCycleHook.test.ts`
  — redirect to `#feedback`, router.isReady guard, id guard, loading skeleton.
  `npm test -- __tests__/reviewCycleHook.test.ts` passes. (Completed 2026-03-18)
- [x] Keep the existing `useApprovals`, `useComments`, `useProjectReviewers`
  hooks but compose them under a new `useReviewCycle(projectId)` hook.
  Added 30 tests in `frontend/__tests__/reviewCycleHook.test.ts` covering interface,
  composition, and derived-field pure logic.
  `npm test -- __tests__/reviewCycleHook.test.ts` passes. (Completed 2026-03-18)

The verified audit-log wiring, lifecycle webhook wiring, and review-cycle E2E
coverage were moved to `docs/latest_features.md` on 2026-03-12.

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

The verified backend FSV proxy layer (`FEDERAL_STYLE_VALIDATOR_URL`,
conditional preflight/regulatory/ML proxying, and `GET /fsv/status`) was moved
to `docs/latest_features.md` on 2026-03-12.

- [ ] Remove `regulatory.py` duplicate pattern matching once FSV proxy is live.

**Phase 2 — Editor integration (prerequisite: FSV TipTap plugin exists)**

- [ ] Register FSV's TipTap plugin in `frontend/extensions/registry.ts`.
- [ ] Remove `tiptapFederalStyleLint.ts` (local reimplementation) once FSV plugin is wired in.
2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited FSV frontend suites were rerun successfully.

- [x] Add sidebar panel showing live FSV validation summary and overall score.
  `frontend/__tests__/fsvEditorAndProject.test.ts` covers Validation Summary
  section: score, grade, issue_count, source, color thresholds, conditional
  render after save. `npm test -- __tests__/fsvEditorAndProject.test.ts`
  passes. (Completed 2026-03-18)
- [x] Configure FSV endpoint URL in the editor plugin via DocReview360's
  settings API. Created `frontend/__tests__/fsvUrlSettings.test.ts` — 21 tests:
  tools page loads FSV URL from `GET /admin/settings/fsv-url`, saves via `PUT` with
  `{url}` body, input state management, disabled-when-unchanged guard, FEDERAL_STYLE_VALIDATOR_URL
  env var reference, editor uses `/documents/preflight` (not FSV directly), `get_fsv_url()`
  env→settings fallback chain, `is_fsv_configured()` export, admin-only guard.
  `npm test -- __tests__/fsvUrlSettings.test.ts` passes. (Completed 2026-03-18)

**Phase 3 — UX consistency and on-save validation**

The FSV experience must be identical whether running standalone in a browser or
inside DocReview360 under Tools. This establishes a consistent brand.

- [ ] Ensure the `/tools/checker` page renders FSV results using the same visual
  layout, color scheme, and severity icons. The current implementation is only
  partially verified; the checklist itself still notes parity is pending FSV's
  published design tokens. Add screenshot or UI regression coverage once the
  target tokens are defined.
- [x] Add on-save validation. `frontend/__tests__/fsvEditorAndProject.test.ts`
  — 9 tests: POST to `/documents/preflight`, `document_id` in body,
  `autoValidationEnabled` gate, fire-and-forget `.catch`, `setValidationSummary`
  called with score/grade/issue_count/source.
  `npm test -- __tests__/fsvEditorAndProject.test.ts` passes. (Completed 2026-03-18)
- [x] Display minimal FSV feedback in the editor toolbar. `fsvEditorAndProject.test.ts`
  — 7 tests: score %, grade, issue_count, source, color thresholds, conditional
  render, toolbar panel presence.
  `npm test -- __tests__/fsvEditorAndProject.test.ts` passes. (Completed 2026-03-18)
- [x] Quality badge added next to "Edit Document" CTA in **Project View**.
  `fsvEditorAndProject.test.ts` — 5 tests: fsvEnabled gate, quality_score %,
  plain_language_grade, color coding (green/amber/red), null guard.
  `npm test -- __tests__/fsvEditorAndProject.test.ts` passes. (Completed 2026-03-18)
- [x] Make on-save validation configurable. `fsvEditorAndProject.test.ts`
  verifies tools page fetches auto-validation state, editor reads it on mount,
  `toggleAutoValidation` PUT flow.
  `npm test -- __tests__/fsvEditorAndProject.test.ts` passes. (Completed 2026-03-18)

**Phase 4 — Core Tool Pack designation**

FSV is the Core Tool Pack for DocReview360 — enabled by default for all orgs.

- [x] Designate FSV as the "Core" tool in the plugin marketplace. `fsvEditorAndProject.test.ts`
  verifies `isCore: true` on FSV entry, `CoreBadge` renders for core tools.
  `npm test -- __tests__/fsvEditorAndProject.test.ts` passes. (Completed 2026-03-18)
- [x] Administrators can disable FSV in Tools page. `fsvEditorAndProject.test.ts`
  confirms `isBuiltIn` + `togglePlugin` wiring for the FSV-specific toggle.
  `npm test -- __tests__/fsvEditorAndProject.test.ts` passes. (Completed 2026-03-18)
- [x] When FSV is disabled, hide FSV-specific UI. `fsvEditorAndProject.test.ts`
  confirms `fsvEnabled` gate guards quality badge and quality table in project
  view. `npm test -- __tests__/fsvEditorAndProject.test.ts` passes.
  (Completed 2026-03-18)

**Phase 5 — Full cutover and documentation**

- [ ] Confirm no remaining duplicate style/quality logic in DocReview360 source.
  Missing requirement: duplicate local implementations still remain. The open
  Phase 1/2 work above still tracks `regulatory.py` removal and
  `frontend/extensions/tiptapFederalStyleLint.ts` replacement, so the cutover is
  not complete yet. (2026-03-12 verification)

### 41) Editor, integrations, and content management

**Phase 1 — Enterprise content integrations**

The verified Microsoft 365 WOPI host integration was moved to
`docs/latest_features.md` on 2026-03-12.

**Phase 2 — Editor hardening**

2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited editor-hardening suite was rerun successfully.

- [x] Add offline editing support. Added `frontend/__tests__/offlineStorage.test.ts`
  — 13 tests covering saveOfflineDraft, loadOfflineDraft, markSynced, getPendingDrafts,
  and clearDraft via the localStorage fallback path (used in jsdom and private browsing).
  `npm test -- __tests__/offlineStorage.test.ts` passes. (Completed 2026-03-18)
The verified format-fidelity expansion (RTF, ODT, EPUB, LaTeX, and Confluence
wiki markup) was moved to `docs/latest_features.md` on 2026-03-12.

**Phase 3 — Enterprise search and analytics**

The verified external-search stub and analytics dashboard/export endpoints were
moved to `docs/latest_features.md` on 2026-03-12.

### 42) Configuration and extensibility

2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited theming suite was rerun successfully.

- [x] Add theme and white-label support. Added `frontend/__tests__/useTheme.test.ts`
  — 10 tests covering CSS custom property injection for all 4 branding color
  variables and removal when null.
  `npm test -- __tests__/useTheme.test.ts` passes. (Completed 2026-03-18)

### 45) Role-based dashboard UX improvements

Dashboards exist for User, Manager, and Admin roles with proper RBAC enforcement
and per-widget visibility customization. The following items improve discoverability
and role-appropriate navigation.

2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited dashboard/sidebar suite was rerun successfully.

- [x] Add a **settings cog icon** to each dashboard header (User, Manager,
  Admin). Added `frontend/__tests__/dashboardAndSidebar.test.ts` — 4 tests
  confirming customize/settings action across all 3 dashboard variants.
  `npm test -- __tests__/dashboardAndSidebar.test.ts` passes. (Completed 2026-03-18)
- [x] Gate dashboard links in the sidebar by role. Source-level tests in
  `dashboardAndSidebar.test.ts` verify isAdmin read, roles read, dashboardNav
  role-based selection, and isAdmin-gated admin sections.
  `npm test -- __tests__/dashboardAndSidebar.test.ts` passes. (Completed 2026-03-18)
- [x] Persist widget visibility preferences to SQLite. Frontend tests in
  `dashboardAndSidebar.test.ts` cover state/visibility.ts API endpoint, PUT
  method, authenticatedFetch usage, and settings.tsx UI contract.
  `npm test -- __tests__/dashboardAndSidebar.test.ts` passes. (Completed 2026-03-18)

### 46) Frontend localization readiness

Backend i18n infrastructure is complete (`i18n.py`, 70 keys, 4 locales, REST
endpoints). Frontend locale JSON files exist in `public/locales/`. Next.js i18n
routing is configured. However, **zero frontend components use the i18n system** —
all UI strings are hardcoded in English.

**Phase 1 — Hook and switcher**

2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited localization suites were rerun successfully.

- [x] Created `frontend/lib/useTranslation.ts` hook. Added `frontend/__tests__/useTranslation.test.ts`
  — 24 tests covering `_dotGet`, `_buildNested`, t() resolution chain, locale persistence,
  and URL routing for translations vs. terminology.
  `npm test -- __tests__/useTranslation.test.ts` passes. (Completed 2026-03-18)
- [x] Created `frontend/components/LocaleSwitcher.tsx` dropdown with 4 locales.
  Added `frontend/__tests__/LocaleSwitcher.test.tsx` — 5 tests covering render,
  selection state, and setLocale call contract.
  `npm test -- __tests__/LocaleSwitcher.test.tsx` passes. (Completed 2026-03-18)
The verified backend locale-preference endpoints were moved to
`docs/latest_features.md` on 2026-03-12.

**Phase 2 — String extraction and migration**

- [x] Extract hardcoded UI strings from `login.tsx`, `projects/index.tsx`, and
  `dashboard/user.tsx`. Pages confirmed to use `useTranslation` + `t()` calls.
  `helpAndSidebar.test.ts` verifies locale keys exist in all 4 locale files.
  `npm test -- __tests__/helpAndSidebar.test.ts` passes. (Completed 2026-03-18)
- [x] Replace hardcoded strings with `t("key")` calls in `login.tsx`,
  `projects/index.tsx`, and `dashboard/user.tsx`. Source-level verification in
  `frontend/__tests__/helpAndSidebar.test.ts` — 6 tests across 4 locales.
  `npm test -- __tests__/helpAndSidebar.test.ts` passes. (Completed 2026-03-18)
- [x] `LocaleSwitcher` added to sidebar footer. Sidebar source confirmed to
  include `LocaleSwitcher`; `helpAndSidebar.test.ts` asserts the import.
  `npm test -- __tests__/helpAndSidebar.test.ts` passes. (Completed 2026-03-18)

**Phase 3 — Full coverage**

- [x] Migrate remaining pages and components to use `useTranslation`. Source
  assertions in `frontend/__tests__/i18nPhase3.test.ts` confirm `search.tsx`,
  `configuration/index.tsx`, and `profile.tsx` import and use `useTranslation`.
  `npm test -- __tests__/i18nPhase3.test.ts` passes. (Completed 2026-03-18)
- [x] Added `frontend/scripts/check-hardcoded-strings.mjs` lint script
  (`npm run lint:i18n`). `i18nPhase3.test.ts` verifies: script exits 0,
  emits [i18n-lint] output, detects JSX text and attribute violations, skips
  t()-wrapped lines, and scans `pages/` + `components/`.
  `npm test -- __tests__/i18nPhase3.test.ts` passes. (Completed 2026-03-18)
- [x] Branding/terminology overrides now applied on top of locale translations
  via `GET /i18n/terminology/{locale}?org_id=`. `i18nPhase3.test.ts` — 7 source
  tests confirm orgId URL construction, separate query key, cache invalidation,
  and graceful fallback. Added an explicit empty-strings fallback in
  `frontend/lib/useTranslation.ts` while preserving public locale-bundle fallback.
  `npm test -- __tests__/i18nPhase3.test.ts` passes. (Completed 2026-03-18)

### 47) In-app support and documentation

A "Support" link exists in the sidebar and the footer shows configurable
Support/Docs/Security/Privacy links via the branding system. However, the actual
help and documentation pages are stubs.

2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited help/support suite was rerun successfully.

- [x] Replaced `/docs/` placeholder with real in-app help. Five-tab layout now
  covered by `frontend/__tests__/helpAndSidebar.test.ts` — Getting Started,
  Key Concepts, FAQ, Keyboard Shortcuts, and API Reference tabs verified.
  `npm test -- __tests__/helpAndSidebar.test.ts` passes. (Completed 2026-03-18)
- [x] Flesh out `/help` content. `helpAndSidebar.test.ts` verifies key-concepts,
  FAQ items (FAQ_ITEMS constant + `q:` entries), keyboard-shortcut section, and
  API Reference section. `npm test -- __tests__/helpAndSidebar.test.ts` passes.
  (Completed 2026-03-18)
- [x] Sidebar "Support" link replaced with collapsible "Help & Support"
  section. `helpAndSidebar.test.ts` asserts label text, `/help#getting-started`
  link, and `/help#shortcuts` link.
  `npm test -- __tests__/helpAndSidebar.test.ts` passes. (Completed 2026-03-18)
- [x] Added `HelpTooltip` component with popover. `helpAndSidebar.test.ts`
  verifies component file exists and renders a Popover/Tooltip element.
  `npm test -- __tests__/helpAndSidebar.test.ts` passes. (Completed 2026-03-18)
- [x] Wire `brandingSupportUrl` and `brandingDocsUrl`. `helpAndSidebar.test.ts`
  verifies sidebar reads both branding URLs and uses `brandingDocsUrl` in an
  href. `npm test -- __tests__/helpAndSidebar.test.ts` passes.
  (Completed 2026-03-18)

### 48) Tool architecture cleanup and configuration persistence

The plugin marketplace and tool configuration system works but has architectural
gaps that affect reliability and simplicity.

**Tool state persistence**

The verified built-in toggle persistence and per-org tool configuration were
moved to `docs/latest_features.md` on 2026-03-12.

**Grammar tool audit**

The verified grammar/spell-plugin categorization work was moved to
`docs/latest_features.md` on 2026-03-12.

**Duplicate logic removal**

2026-03-18 backend verification note: `tests/test_item48_validate.py` now
passes. Verification included fixing FastAPI import blockers so the app loads
cleanly under the current dependency set, then rerunning the targeted suite.

- [x] Consolidated three separate validation endpoints into
  `POST /documents/validate`. Added `tests/test_item48_validate.py` — 22 tests
  covering endpoint contract, selective check execution, authentication,
  and per-category FSV settings persistence.
  `.venv/bin/pytest -q tests/test_item48_validate.py` passes. (Completed 2026-03-18)

**Tool configurability**

- [x] Add per-check granularity for FSV rules in the admin Configuration →
  Tools page. Category persistence tested in `tests/test_item48_validate.py`
  (GET/PUT /admin/settings/fsv-checks round-trip).
  `.venv/bin/pytest -q tests/test_item48_validate.py` passes. (Completed 2026-03-18)
2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited tools-index suite was rerun successfully.

- [x] Tools index page now shows Active/Disabled/Not-installed status badges,
  community labels, dimmed disabled cards, admin-only Configure links, and
  Enable/Disable toggles for built-in plugins. Added
  `frontend/__tests__/toolsIndexPage.test.ts` — 24 tests covering all states,
  gating logic, toggle endpoint wiring, and getStatus return values.
  `npm test -- __tests__/toolsIndexPage.test.ts` passes. (Completed 2026-03-18)

### 49) Frontend stability — React hook violations and stale crashes

Pages crash in production with "Rendered more hooks than during the previous
render" or "Rendered fewer hooks than expected". The root cause is React's Rules
of Hooks being violated: hooks must be called in the **same order on every
render** and **never after a conditional return**. Tests miss this because Jest +
Testing Library hydrate synchronously and never hit the loading/null states that
trigger early returns. The "stale" message users see is React or Next.js
detecting that the previous render's hook count differs from the current one.

**Regression coverage still required**

2026-03-18 verification note: the shared frontend Vitest blocker from item 43d
is resolved, and the cited hook-regression suites were rerun successfully.

- [x] `pages/projects/[id]/index.tsx`: Added `frontend/__tests__/hookOrderRegression.test.ts`
  source-level regression guard confirming `feedbackShowMyOnly` is declared before
  conditional early returns.
  `npm test -- __tests__/hookOrderRegression.test.ts` passes. (Completed 2026-03-18)

- [x] **`router.isReady` guard added** to the affected dynamic pages. Source-level
  test in `hookOrderRegression.test.ts` verifies the guard is present and
  `router.query.id` is not accessed without it.
  `npm test -- __tests__/hookOrderRegression.test.ts` passes. (Completed 2026-03-18)

- [x] **Stale closures fixed** in `pages/projects/[id]/index.tsx`. Addressed via
  source-level assertions in `hookOrderRegression.test.ts`; dependency-array
  changes are present in code.
  `npm test -- __tests__/hookOrderRegression.test.ts` passes. (Completed 2026-03-18)

- [x] **React Error Boundary added**. Added `frontend/__tests__/PageErrorBoundary.test.tsx`
  — 7 tests covering fallback UI, error display, Try-again reset, and
  resetKey-based route-change auto-reset.
  `npm test -- __tests__/PageErrorBoundary.test.tsx` passes. (Completed 2026-03-18)

- [x] **`useApprovals` `any` type removed**. `RawApproval` and `mapApproval` verified
  in `hookOrderRegression.test.ts` — interface definition, mapper usage, field
  types, and state cast confirmed.
  `npm test -- __tests__/hookOrderRegression.test.ts` passes. (Completed 2026-03-18)

**Still open**

- [ ] **Hook ordering in `useProject`, `useApprovals`, `usePhases`** — hooks receive
  `undefined` during router hydration but the queries are `enabled: !!id` so no
  fetch fires. The ordering is stable because no hooks are called conditionally.
  No crash observed; keep under monitoring. (2026-03-12)

- [ ] **Frontend tests do not cover loading → loaded state transitions** — added
  `frontend/__tests__/hookLoadingStates.test.ts` (24 tests): verifies `enabled: !!id`
  guards on `useProject`/`useApprovals`/`usePhases`, `router.isReady` guard in
  `projects/[id]/index.tsx`, `ErrorBoundary` + `QueryClientProvider` in `_app.tsx`,
  and `authenticatedFetch` in all hooks (interceptable by MSW when installed).
  `npm test -- __tests__/hookLoadingStates.test.ts` passes, but full MSW
  delayed-response tests are still deferred until `msw` is added as a dev
  dependency, so this item remains open. (2026-03-18 verification)

### 50) iOS companion app — backend readiness

An iOS companion app is under consideration with limited scope: comment review,
approval workflows, markup viewer, and assigned projects. The backend API is
already 100% JSON with Pydantic models and has API versioning (`/api/v1/`), CORS,
and rate limiting in place. The items below address the gaps that would block or
degrade a native mobile client.

**What's already mobile-ready (no work needed):**

- JSON-only API with Pydantic response models (OpenAPI schema at `/openapi.json`)
- API versioning (URL-path `/api/v1/`, backward-compatible)
- CORS configuration (native apps bypass CORS, but hybrid/WebView apps benefit)
- Rate limiting with `Retry-After` header (Redis + in-memory fallback)
- OIDC + PKCE authorization code flow (safe for native apps)
- Session tracking per device (`UserSessionRecord`, idle timeout, concurrent limit)
- Token revocation (`revoked_tokens` SQLite table, checked on every request)
- Bearer token auth via `Authorization` header (no cookie dependency)
- File upload with chunked streaming (`POST /documents/import`)

**Phase 1 — Auth and token lifecycle (required before any mobile client)**

- [x] Add refresh token support. Current JWT access tokens expire after 30 minutes
  with no way to renew without re-authenticating. Mobile apps need a
  `POST /token/refresh` endpoint that accepts a long-lived refresh token (stored
  securely in iOS Keychain) and returns a new short-lived access token.
  Considerations: refresh token rotation (one-time use), revocation, family
  detection (reuse = compromise → revoke family).
- [x] Add `expires_in` (seconds) to the `Token` response model. iOS clients need
  this to schedule proactive token refresh (e.g., at 80% of lifetime). The current
  response only includes `access_token` and `token_type`.
- [x] Ensure `POST /token` works with `application/json` body (not just form-encoded).
  Native HTTP clients prefer JSON; FastAPI's `OAuth2PasswordRequestForm` expects
  form data. Add a parallel JSON login endpoint or accept both content types.

**Phase 2 — Pagination on list endpoints (required for mobile bandwidth)**

- [ ] Add `skip` and `limit` query parameters to list endpoints. Mobile clients on
  cellular connections cannot afford unbounded response sizes. Priority endpoints:
  - `GET /projects` — returns all projects; needs pagination + total count
  - `GET /projects/{id}/feedback` — can grow large; needs cursor or offset pagination
  - `GET /projects/{id}/assignments` — moderate size but should be consistent
  - `GET /projects/{id}/notification-log` — unbounded; needs pagination
  - `GET /documents` — returns all documents; needs pagination
  - `GET /comments/{project_id}` — can grow large with inline comments
- [ ] Return pagination metadata in responses: `{ items: [...], total: N, skip: 0, limit: 20 }`.
  Consider a shared `PaginatedResponse[T]` generic model.

**Phase 3 — Push notifications (required for useful mobile experience)**

- [ ] Add device token registration: `POST /devices/register` (accepts platform,
  device token, optional device name) and `DELETE /devices/{token}`. Store in a
  `device_tokens` SQLite table keyed by user + platform.
- [ ] Integrate Apple Push Notification service (APNs). Use token-based auth
  (`.p8` key) rather than certificate-based. Priority notification events for the
  iOS app: `review.assigned`, `review.reminder`, `approval.requested`,
  `approval.completed`, `comment.added`, `document.updated`.
- [ ] Extend `send_notification()` in `notifications.py` to dispatch to APNs
  alongside existing Slack/Teams/email/webhook channels. Respect per-user
  notification preferences (already stored via settings API).
- [ ] Add notification badge count endpoint: `GET /notifications/unread-count`
  for iOS badge number updates.

**Phase 4 — API ergonomics for mobile (nice-to-have, not blocking)**

- [ ] Add a lightweight "my assignments" summary endpoint:
  `GET /assignments/me/summary` — returns open assignments across all projects
  with project name, document title, status, and due date. Avoids the mobile app
  needing to fetch all projects then query each one for assignments.
- [ ] Add `Content-Length` headers on file download responses for iOS progress
  indicators (`URLSession` `countOfBytesExpectedToReceive`).
- [ ] Secure WebSocket auth. The current `/ws/dashboard` accepts an unvalidated
  `?user=` query param. Mobile clients should pass a JWT:
  `?token=<jwt>` validated server-side before accepting the connection.
- [ ] Consider a compact document-view endpoint that returns rendered HTML or
  a lightweight markup summary suitable for a mobile read-only viewer, without
  needing the full TipTap JSON structure.
- [ ] Add `X-RateLimit-Remaining` and `X-RateLimit-Reset` response headers so
  the iOS networking layer can throttle proactively.

**Phase 5 — iOS-specific infrastructure (outside this codebase, listed for planning)**

- [ ] Generate Swift API client from OpenAPI schema (`/openapi.json`). Tools:
  `swift-openapi-generator` (Apple's official) or `CreateAPI`.
- [ ] Design iOS Keychain storage strategy for refresh tokens and PKCE verifiers.
- [ ] Plan offline-first architecture: local Core Data cache for assignments and
  comments, background sync via `BGAppRefreshTask`.
- [ ] Evaluate whether the markup viewer should use a `WKWebView` rendering the
  existing HTML output or a native SwiftUI document renderer.
- [ ] Set up TestFlight distribution and App Store Connect metadata.

**Implementation notes:**

Phases 1–2 benefit the web frontend too (refresh tokens prevent the current
silent-logout-after-30-minutes UX issue; pagination improves dashboard load times
on large deployments). Phase 3 is iOS-specific but the device registration
endpoint and `send_notification()` extension are reusable for a future Android
companion. Phase 4 items are quality-of-life improvements that can be done
incrementally. Phase 5 is entirely outside this repository.

---

ADDED BY USER

- [ ] I logged in as Alice, created a project and assigned Bob to review. I logged off as Alice and logged in as Bob. I see the assigned project in Project view, but not Dashboard.
- [ ] Separately, I logged in as Bob, went to Dashboard view and got this.

1/2

Next.js 16.1.5 (stale)
Turbopack
Runtime TypeError



Failed to fetch
lib/api.ts (66:18) @ authenticatedFetch


  64 |
  65 |   try {
> 66 |     return await fetch(fullUrl, {
     |                  ^
  67 |       ...options,
  68 |       headers,
  69 |       credentials: "include",
Call Stack
27

Show 25 ignore-listed frame(s)
authenticatedFetch
lib/api.ts (66:18)
UserDashboardPage.useQuery
pages/dashboard/user.tsx (103:41)

- [ ] I logged in, went to a project, clicked Edit Document. Although the entire webpage contains TipTap, the authoring window itself (authoring area) is only a small portion of the page. If the TipTap environment fills the page, the authoring window should be roughly the same size.
- [ ] In TipTap editor, I typed a few lines, clicked unordered (bulleted) and ordered (numbered) and while the lines indented, none showed the bullets or numbers.
- [ ] In TipTap editor, I wasn't sure what Enable Indentation was, so I clicked it and got this:

1/2

Next.js 16.1.5 (stale)
Turbopack
Runtime TypeError



editor.can(...).chain(...).focus(...).indent is not a function
pages/editors/tiptap.tsx (1454:52) @ TipTapEditorPage


  1452 |           formattingLocked ||
  1453 |             !indentationEnabled ||
> 1454 |             !(editor.can().chain() as any).focus().indent().run(),
       |                                                    ^
  1455 |         )}
  1456 |         {toolbarButton(
  1457 |           <IndentDecrease className="w-4 h-4" />,
Call Stack
15

Show 14 ignore-listed frame(s)
TipTapEditorPage
pages/editors/tiptap.tsx (1454:52)

- [ ] In TipTap editor, I added a heading 1, clicked Enable Heading Lock and nothing happened. I was still able to edit the heading.
- [ ] In TipTap editor, I tried to open a template and got this.

1/1

Next.js 16.1.5 (stale)
Turbopack
Runtime Error



{"detail":"Not Found"}
pages/editors/tiptap.tsx (1101:26) @ TipTapEditorPage.useCallback[handleTemplateLoad]


  1099 |     try {
  1100 |       const res = await api.fetchTemplate(filename);
> 1101 |       if (!res.ok) throw new Error(await res.text());
       |                          ^
  1102 |       const data = await res.json();
  1103 |       const sanitized = sanitizeHtml(data.content || "");
  1104 |       if (!sanitized || sanitized.trim().length === 0) {
Call Stack
1

TipTapEditorPage.useCallback[handleTemplateLoad]
pages/editors/tiptap.tsx (1101:26)

- [ ] In TipTap editor, I tried to open API template and got this.

Failed to load template: doc_type::API Manual / API Reference

Error: {"detail":"Not Found"}

- [ ] In TipTap Editor, I tried to open Briefing/Slide Deck template and got this.

Failed to load template: doc_type::Briefing / Slide Deck

Error: {"detail":"Not Found"}

- [ ] In Help & Support, I clicked the About button > GitHub Repository, and got an error. This is the correct URL: https://github.com/eputnam77/DocReview360

- [ ] This is from the audit log. There are many 404 errors.

INFO:     127.0.0.1:58996 - "GET /audit?entity_id=demo-bob HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:58996 - "GET /audit?entity_id=demo-bob HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:54701 - "GET /projects/demo-bob/review-summary HTTP/1.1" 200 OK
INFO:     127.0.0.1:58996 - "GET /templates HTTP/1.1" 200 OK
INFO:     127.0.0.1:54701 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:54701 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:54161 - "GET /templates HTTP/1.1" 200 OK
INFO:     127.0.0.1:55342 - "GET /projects/demo-bob/feedback HTTP/1.1" 200 OK
INFO:     127.0.0.1:50427 - "GET /projects/demo-bob HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/reviewers HTTP/1.1" 200 OK
INFO:     127.0.0.1:59793 - "GET /projects/demo-bob/reviews?phase=draft HTTP/1.1" 200 OK
INFO:     127.0.0.1:50672 - "GET /projects/demo-bob/assignments HTTP/1.1" 200 OK
INFO:     127.0.0.1:54859 - "GET /users HTTP/1.1" 200 OK
INFO:     127.0.0.1:59793 - "GET /projects/demo-bob/assignments/me HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/review-summary HTTP/1.1" 200 OK
INFO:     127.0.0.1:55342 - "GET /projects/demo-bob/feedback/progress HTTP/1.1" 200 OK
INFO:     127.0.0.1:50672 - "GET /projects/demo-bob/lifecycle HTTP/1.1" 200 OK
INFO:     127.0.0.1:50427 - "GET /projects/demo-bob/notification-log HTTP/1.1" 200 OK
INFO:     127.0.0.1:54859 - "GET /projects/demo-bob/sla-summary HTTP/1.1" 200 OK
INFO:     127.0.0.1:50672 - "GET /audit?entity_id=demo-bob HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:50672 - "GET /audit?entity_id=demo-bob HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:59793 - "POST /projects/demo-bob/assignments/view HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/sla-deadlines HTTP/1.1" 200 OK
INFO:     127.0.0.1:55342 - "POST /projects/demo-bob/assignments/view HTTP/1.1" 200 OK
INFO:     127.0.0.1:50427 - "GET /projects/demo-bob/documents/scores HTTP/1.1" 200 OK
INFO:     127.0.0.1:54859 - "GET /plugin-marketplace/builtin-status HTTP/1.1" 200 OK
INFO:     127.0.0.1:55342 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:54859 - "GET /environments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:50427 - "GET /i18n/translations/en HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:59793 - "GET /plugin-marketplace/builtin-status HTTP/1.1" 403 Forbidden        
INFO:     127.0.0.1:55342 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /users HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:54859 - "GET /environments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:50672 - "GET /projects/demo-bob HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:50427 - "GET /projects/demo-bob/assignments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:59793 - "GET /projects/demo-bob/feedback HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:55342 - "GET /projects/demo-bob/feedback/progress HTTP/1.1" 403 Forbidden      
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/notification-log HTTP/1.1" 403 Forbidden       
INFO:     127.0.0.1:54859 - "GET /projects/demo-bob/review-summary HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:50672 - "GET /projects/demo-bob/assignments/me HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:50427 - "GET /projects/demo-bob/lifecycle HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:59793 - "GET /projects/demo-bob/sla-summary HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:55342 - "GET /projects/demo-bob/sla-deadlines HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/documents/scores HTTP/1.1" 403 Forbidden       
INFO:     127.0.0.1:54859 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /environments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /i18n/translations/en HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /users HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /plugin-marketplace/builtin-status HTTP/1.1" 403 Forbidden        
INFO:     127.0.0.1:53395 - "GET /environments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/assignments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/feedback HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/feedback/progress HTTP/1.1" 403 Forbidden      
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/notification-log HTTP/1.1" 403 Forbidden       
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/review-summary HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/assignments/me HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/lifecycle HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/sla-summary HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/sla-deadlines HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob/documents/scores HTTP/1.1" 403 Forbidden       
INFO:     127.0.0.1:53395 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects/demo-bob HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:53395 - "GET /projects HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:60904 - "POST /token HTTP/1.1" 200 OK
INFO:     127.0.0.1:60904 - "GET /users/me HTTP/1.1" 200 OK
INFO:     127.0.0.1:60904 - "GET /profile HTTP/1.1" 200 OK
INFO:     127.0.0.1:60904 - "GET /projects HTTP/1.1" 200 OK
INFO:     127.0.0.1:60904 - "GET /profile HTTP/1.1" 200 OK
INFO:     127.0.0.1:62661 - "GET /rbac/role-permissions HTTP/1.1" 200 OK
INFO:     127.0.0.1:63619 - "GET /profile HTTP/1.1" 200 OK
INFO:     127.0.0.1:62661 - "GET /rbac/role-permissions HTTP/1.1" 200 OK
INFO:     127.0.0.1:58889 - "OPTIONS /projects/demo-alice HTTP/1.1" 200 OK
INFO:     127.0.0.1:50809 - "OPTIONS /projects/demo-alice/feedback HTTP/1.1" 200 OK
INFO:     127.0.0.1:50362 - "OPTIONS /projects/demo-alice/feedback/progress HTTP/1.1" 200 OK       
INFO:     127.0.0.1:62878 - "OPTIONS /projects/demo-alice/assignments HTTP/1.1" 200 OK
INFO:     127.0.0.1:58308 - "OPTIONS /projects/demo-alice/review-summary HTTP/1.1" 200 OK
INFO:     127.0.0.1:61061 - "OPTIONS /projects/demo-alice/notification-log HTTP/1.1" 200 OK        
INFO:     127.0.0.1:50809 - "OPTIONS /projects/demo-alice/lifecycle HTTP/1.1" 200 OK
INFO:     127.0.0.1:58889 - "OPTIONS /projects/demo-alice/assignments/me HTTP/1.1" 200 OK
INFO:     127.0.0.1:50362 - "OPTIONS /projects/demo-alice/sla-summary HTTP/1.1" 200 OK
INFO:     127.0.0.1:62878 - "OPTIONS /projects/demo-alice/sla-deadlines HTTP/1.1" 200 OK
INFO:     127.0.0.1:61061 - "OPTIONS /audit?entity_id=demo-alice HTTP/1.1" 200 OK
INFO:     127.0.0.1:58308 - "OPTIONS /projects/demo-alice/assignments/view HTTP/1.1" 200 OK        
INFO:     127.0.0.1:50809 - "OPTIONS /projects/demo-alice/documents/scores HTTP/1.1" 200 OK        
INFO:     127.0.0.1:50362 - "OPTIONS /audit?entity_id=demo-alice HTTP/1.1" 200 OK
INFO:     127.0.0.1:58889 - "OPTIONS /projects/demo-alice/assignments/view HTTP/1.1" 200 OK        
INFO:     127.0.0.1:50517 - "GET /projects/demo-alice HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/feedback HTTP/1.1" 200 OK
INFO:     127.0.0.1:58889 - "OPTIONS /projects/demo-alice/reviews?phase=draft HTTP/1.1" 200 OK
INFO:     127.0.0.1:50362 - "OPTIONS /projects/demo-alice/reviewers HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "GET /projects/demo-alice/feedback/progress HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/assignments HTTP/1.1" 200 OK
INFO:     127.0.0.1:50362 - "OPTIONS /projects/demo-alice/assignments/179e034e-0aed-45c0-b60e-bc291c64ae2e/eligibility HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "GET /projects/demo-alice/review-summary HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/notification-log HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "GET /projects/demo-alice/lifecycle HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/assignments/me HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/sla-deadlines HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "GET /projects/demo-alice/sla-summary HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /audit?entity_id=demo-alice HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:50517 - "POST /projects/demo-alice/assignments/view HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/documents/scores HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/reviews?phase=draft HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "POST /projects/demo-alice/assignments/view HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "GET /projects/demo-alice/assignments/179e034e-0aed-45c0-b60e-bc291c64ae2e/eligibility HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /projects/demo-alice/reviewers HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "GET /audit?entity_id=demo-alice HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:50517 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /templates HTTP/1.1" 200 OK
INFO:     127.0.0.1:50517 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:56991 - "GET /templates HTTP/1.1" 200 OK
INFO:     127.0.0.1:63586 - "OPTIONS /ai/rewrite HTTP/1.1" 200 OK
INFO:     127.0.0.1:55202 - "POST /ai/rewrite HTTP/1.1" 200 OK
INFO:     127.0.0.1:58048 - "OPTIONS /templates/doc_type%3A%3AICR HTTP/1.1" 200 OK
INFO:     127.0.0.1:49745 - "GET /templates/doc_type%3A%3AICR HTTP/1.1" 200 OK
INFO:     127.0.0.1:58048 - "OPTIONS /templates/doc_type%3A%3AManual%20/%20Handbook HTTP/1.1" 200 OK
INFO:     127.0.0.1:49745 - "GET /templates/doc_type%3A%3AManual%20/%20Handbook HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:61377 - "OPTIONS /templates/doc_type%3A%3AMemorandum HTTP/1.1" 200 OK
INFO:     127.0.0.1:65265 - "GET /templates/doc_type%3A%3AMemorandum HTTP/1.1" 200 OK
INFO:     127.0.0.1:61377 - "OPTIONS /templates/doc_type%3A%3AFinal%20Rule HTTP/1.1" 200 OK
INFO:     127.0.0.1:65265 - "GET /templates/doc_type%3A%3AFinal%20Rule HTTP/1.1" 200 OK
INFO:     127.0.0.1:61377 - "OPTIONS /templates/doc_type%3A%3AGuidance HTTP/1.1" 200 OK
INFO:     127.0.0.1:65265 - "GET /templates/doc_type%3A%3AGuidance HTTP/1.1" 200 OK
INFO:     127.0.0.1:61377 - "OPTIONS /templates/doc_type%3A%3ADesk%20Guide HTTP/1.1" 200 OK
INFO:     127.0.0.1:65265 - "GET /templates/doc_type%3A%3ADesk%20Guide HTTP/1.1" 200 OK
INFO:     127.0.0.1:61377 - "OPTIONS /templates/doc_type%3A%3AFAQ HTTP/1.1" 200 OK
INFO:     127.0.0.1:65265 - "GET /templates/doc_type%3A%3AFAQ HTTP/1.1" 200 OK
INFO:     127.0.0.1:61377 - "OPTIONS /templates/doc_type%3A%3AAPI%20Manual%20/%20API%20Reference HTTP/1.1" 200 OK
INFO:     127.0.0.1:65265 - "GET /templates/doc_type%3A%3AAPI%20Manual%20/%20API%20Reference HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:55082 - "OPTIONS /templates/faa_ac HTTP/1.1" 200 OK
INFO:     127.0.0.1:53343 - "GET /templates/faa_ac HTTP/1.1" 200 OK
INFO:     127.0.0.1:55082 - "OPTIONS /templates/doc_type%3A%3AAdvisory%20Circular HTTP/1.1" 200 OK
INFO:     127.0.0.1:53343 - "GET /templates/doc_type%3A%3AAdvisory%20Circular HTTP/1.1" 200 OK
INFO:     127.0.0.1:55082 - "OPTIONS /templates/doc_type%3A%3AAfter-Action%20Report HTTP/1.1" 200 OK
INFO:     127.0.0.1:53343 - "GET /templates/doc_type%3A%3AAfter-Action%20Report HTTP/1.1" 200 OK
INFO:     127.0.0.1:55082 - "OPTIONS /templates/doc_type%3A%3AAudit%20Report HTTP/1.1" 200 OK
INFO:     127.0.0.1:53343 - "GET /templates/doc_type%3A%3AAudit%20Report HTTP/1.1" 200 OK
INFO:     127.0.0.1:53343 - "GET /templates/doc_type%3A%3AAudit%20Report HTTP/1.1" 200 OK
INFO:     127.0.0.1:55082 - "OPTIONS /templates/doc_type%3A%3ABriefing%20/%20Slide%20Deck HTTP/1.1"
 200 OK
INFO:     127.0.0.1:53343 - "GET /templates/doc_type%3A%3ABriefing%20/%20Slide%20Deck HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:52649 - "GET /templates/doc_type%3A%3ADesk%20Guide HTTP/1.1" 200 OK
INFO:     127.0.0.1:57839 - "OPTIONS /templates/doc_type%3A%3AFederal%20Register%20Notice HTTP/1.1"
 200 OK
INFO:     127.0.0.1:52649 - "GET /templates/doc_type%3A%3AFederal%20Register%20Notice HTTP/1.1" 200 OK
INFO:     127.0.0.1:57149 - "OPTIONS /i18n/translations/en HTTP/1.1" 200 OK
INFO:     127.0.0.1:53001 - "GET /i18n/translations/en HTTP/1.1" 200 OK
INFO:     127.0.0.1:53041 - "OPTIONS /plugin-marketplace/builtin-status HTTP/1.1" 200 OK
INFO:     127.0.0.1:50520 - "OPTIONS /plugin-marketplace/builtin-status HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /plugin-marketplace/builtin-status HTTP/1.1" 200 OK
INFO:     127.0.0.1:50520 - "OPTIONS /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /plugin-marketplace/builtin-status HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:50520 - "OPTIONS /admin/settings/fsv-checks HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/fsv-checks HTTP/1.1" 200 OK
INFO:     127.0.0.1:50520 - "OPTIONS /admin/settings/fsv-url HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/fsv-checks HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/fsv-url HTTP/1.1" 200 OK
INFO:     127.0.0.1:50520 - "OPTIONS /plugin-marketplace HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/fsv-url HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /plugin-marketplace HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /plugin-marketplace HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /plugin-marketplace/builtin-status HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /plugin-marketplace/builtin-status HTTP/1.1" 200 OK
INFO:     127.0.0.1:52564 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/fsv-checks HTTP/1.1" 200 OK
INFO:     127.0.0.1:52564 - "GET /admin/settings/auto-validation HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/fsv-checks HTTP/1.1" 200 OK
INFO:     127.0.0.1:52564 - "GET /admin/settings/fsv-url HTTP/1.1" 200 OK
INFO:     127.0.0.1:52564 - "GET /plugin-marketplace HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /admin/settings/fsv-url HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /plugin-marketplace HTTP/1.1" 200 OK
INFO:     127.0.0.1:51931 - "OPTIONS /documents HTTP/1.1" 200 OK
INFO:     127.0.0.1:53284 - "GET /documents HTTP/1.1" 200 OK
INFO:     127.0.0.1:64148 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:56351 - "GET /environments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:58898 - "GET /i18n/translations/en HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:64148 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:56351 - "GET /environments HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:64148 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:56351 - "GET /branding HTTP/1.1" 200 OK
INFO:     127.0.0.1:64901 - "GET /profile HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:64901 - "GET /rbac/role-permissions HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:64901 - "GET /profile HTTP/1.1" 403 Forbidden
INFO:     127.0.0.1:64901 - "GET /rbac/role-permissions HTTP/1.1" 403 Forbidden

---

## AI Reliability Architecture Implementation Plan

**Date:** 2026-03-13
**Scope:** Full reliability and stability assessment of DocReview360
**Objective:** Eliminate instability risks from rapid AI-assisted development by
introducing strict contracts, automated reliability gates, deterministic outputs,
strong testing coverage, observability, and security validation.

---

### Reliability Findings

**Overall assessment: Strong foundation with targeted gaps.**

DocReview360 has mature infrastructure in many reliability areas: circuit breakers
on signature providers, structured JSON logging, OpenTelemetry tracing, rate
limiting with Redis/in-memory fallback, audit log integrity verification,
AES-256-GCM column encryption, comprehensive RBAC, CORS hardening, security
headers, and a CI pipeline with ruff/mypy/bandit/pytest/semgrep. The codebase
demonstrates intentional engineering — not accidental stability.

However, rapid feature development has introduced gaps in five areas:

1. **Error response inconsistency** — no unified error envelope across 418 HTTPException raises
2. **API router testing coverage** — 15+ routers (200+ endpoints) have zero dedicated test files
3. **Input validation sparseness** — only 86 constraint annotations across 364 endpoints
4. **Monolithic file risk** — 6 backend files exceed 1,000 lines; 1 frontend page is 3,059 lines
5. **Missing service layer** — business logic scattered between routers and utility modules

---

### Stability Risks

| Risk | Severity | Evidence |
|------|----------|----------|
| Inconsistent error responses break client parsing | Medium | Mix of `{"detail":...}`, `{"error":...}`, `{"ok":false,"message":...}` |
| Untested admin/dashboard/org endpoints regress silently | High | 15+ routers with 0 test files; 200+ endpoints uncovered |
| Large router files (1,000-1,500 lines) resist safe modification | Medium | `admin_router.py` (1,524), `workflows_router.py` (1,256), `tools_router.py` (1,083) |
| `models.py` (721 lines, 42 models) single-point-of-change risk | Medium | Every module imports from it; changes risk cascade |
| Frontend project page (3,059 lines) is fragile under change | Medium | Hook ordering bugs already documented (item 49) |
| 56% of exception handlers have no logging | Low | Intentionally defensive in many cases, but silent failures in notifications and SoD |
| Dependabot placeholder not configured | Low | `.github/dependabot.yml` exists but updates section is empty |
| No global exception handler middleware | Medium | FastAPI defaults used; no structured error envelope enforced |
| Test state pollution causes 49 failures in full suite | Medium | Tests pass in isolation; ordering-dependent failures in CI |
| Missing string-length constraints on text inputs | Low | Names, descriptions, URLs lack min/max length validation |

---

### Missing Infrastructure

| Category | What Exists | What's Missing |
|----------|------------|----------------|
| Error taxonomy | 12+ domain exceptions (`GoogleDriveError`, `SoDViolationError`, etc.) | Unified base `AppError` hierarchy; global exception handler middleware |
| Error response contract | `HTTPException(detail=...)` | `ErrorResponse` Pydantic model enforced via `response_model` on error paths |
| Input constraints | 86 constraint annotations | Systematic `min_length`/`max_length` on strings; `ge`/`le` on numerics |
| Router tests | ML, approvals, auth routers tested | Admin (49 endpoints), dashboards (25), organizations (12), SCIM (16), SLA (9), legal (9), records (7), branches (7), config (21), feedback (14), assignments (25), WOPI (8+) |
| Service layer | Direct router-to-utility calls | `ProjectService`, `DocumentService`, `WorkflowService` classes |
| Configuration schema | `config.py` dataclass, `yaml_loader.py` safe loading | Startup validation that catches misconfiguration before first request |
| Test isolation | Per-test SQLite reset via conftest | Fix for 49 ordering-dependent failures (env monkeypatch pollution) |
| Dependabot | Placeholder YAML | Configured update rules for pip and npm ecosystems |
| Retry standardization | Custom retry in `event_dispatcher.py` and `signatures.py` | Shared `RetryPolicy` utility or `tenacity` adoption |
| Frontend component decomposition | Hooks extracted (`useProject`, `useDocuments`) | Project page split into `<ProjectPhases>`, `<ProjectReviewers>`, `<ProjectFeedback>` etc. |

---

### Implementation Roadmap

---

#### P0 — Critical Reliability Work

These tasks address risks that can cause silent data loss, undetected regressions,
or production failures. Implement before any release.

---

**R-01: Unified Error Response Contract**

Problem:
418 HTTPException raises across 29 routers use inconsistent response shapes.
Clients cannot reliably parse errors. Some return `{"detail": "..."}`, others
`{"error": "..."}`, others `{"ok": false, "message": "..."}`.

Recommendation:
Create a standard `ErrorResponse` model and a global exception handler that
normalizes all errors into a single contract.

Implementation:
1. Create `src/docreview360/errors.py` with:
   - `AppError(Exception)` base class with `code: str`, `detail: str`, `status_code: int`
   - Subclasses: `NotFoundError`, `ForbiddenError`, `ValidationError`, `ProviderError`,
     `ConfigError`, `RetryableError`
   - `ErrorResponse(BaseModel)` with `error: str`, `detail: str`, `trace_id: str | None`
2. Add `@app.exception_handler(AppError)` in `api/__init__.py` that returns
   `JSONResponse(status_code=exc.status_code, content=ErrorResponse(...))`
3. Add `@app.exception_handler(Exception)` as catch-all that logs full traceback
   and returns 500 with trace_id (never leaking internals)
4. Migrate routers incrementally — existing `HTTPException` continues to work

Affected Files:
- `src/docreview360/errors.py` (new)
- `src/docreview360/api/__init__.py`
- All router files (incremental migration)

---

**R-02: Fix Test Suite Ordering Failures**

Problem:
49 tests fail when run together but pass individually. Root cause: tests that
monkeypatch `DOCREVIEW360_ENV` to `production` pollute global state for
subsequent tests. This makes CI results unreliable.

Recommendation:
Fix the test isolation so the full suite passes deterministically.

Implementation:
1. Audit all tests that set `DOCREVIEW360_ENV=production` — ensure they restore
   the original value (use `monkeypatch` fixture which auto-restores)
2. Add `autouse=True` fixture in `conftest.py` that saves and restores all
   `DOCREVIEW360_*` env vars around each test
3. Identify any module-level caches that retain stale env values (e.g.,
   `lru_cache` on config functions) and clear them in fixtures
4. Run `pytest --forked` or `pytest -x` to verify ordering independence
5. Add CI step: `pytest --randomly-seed=last` to catch future pollution

Affected Files:
- `tests/conftest.py`
- `tests/test_coverage_gaps.py` (19 known failures)
- `tests/test_role_403_mfa.py` (2 known failures)
- Any test files using `monkeypatch.setenv("DOCREVIEW360_ENV", "production")`

---

**R-03: API Router Integration Tests for Untested Endpoints**

Problem:
15+ routers covering 200+ endpoints have zero dedicated test files. Regressions
in admin settings, dashboard analytics, organization management, SCIM
provisioning, SLA tracking, legal hold, records management, and WOPI integration
will not be caught.

Recommendation:
Create integration test files for each untested router using the existing
`TestClient` + `_alice_headers()` pattern from `conftest.py`.

Implementation:
Create the following test files, each exercising CRUD + auth + error paths:

| Test File | Router | Min Tests |
|-----------|--------|-----------|
| `tests/api/test_admin_endpoints.py` | `admin_router.py` (49 endpoints) | 30 |
| `tests/api/test_dashboard_endpoints.py` | `dashboards_router.py` (25 endpoints) | 15 |
| `tests/api/test_org_endpoints.py` | `organizations_router.py` (12 endpoints) | 10 |
| `tests/api/test_scim_endpoints.py` | `scim_router.py` (16 endpoints) | 12 |
| `tests/api/test_sla_endpoints.py` | `sla_router.py` (9 endpoints) | 8 |
| `tests/api/test_legal_endpoints.py` | `legal_router.py` (9 endpoints) | 8 |
| `tests/api/test_records_endpoints.py` | `records_router.py` (7 endpoints) | 6 |
| `tests/api/test_branches_endpoints.py` | `branches_router.py` (7 endpoints) | 6 |
| `tests/api/test_config_endpoints.py` | `config_router.py` (21 endpoints) | 12 |
| `tests/api/test_feedback_endpoints.py` | `feedback_router.py` (14 endpoints) | 10 |
| `tests/api/test_assignments_endpoints.py` | `assignments_router.py` (25 endpoints) | 15 |
| `tests/api/test_wopi_endpoints.py` | `wopi_router.py` (8+ endpoints) | 8 |

Each test file should verify:
- Authenticated access required (401 without token)
- Admin-only endpoints reject non-admin users (403)
- Valid requests return expected response shape
- Not-found IDs return 404
- Invalid inputs return 400 or 422

Affected Files:
- `tests/api/` (new directory, 12 new test files)

---

**R-04: Startup Configuration Validation**

Problem:
Misconfigured environment variables cause runtime failures on the first request
rather than failing fast at startup. Examples: invalid `DOCREVIEW360_SECRET_KEY`
length, malformed `DOCREVIEW360_ALLOW_ORIGINS`, unreachable Redis URL.

Recommendation:
Add a configuration validation step that runs during app startup and raises
clear errors before the server accepts connections.

Implementation:
1. Create `src/docreview360/config_validator.py` with a Pydantic `Settings`
   model using `pydantic-settings`:
   - `secret_key: str` with `min_length=32` (prod only)
   - `allow_origins: list[str]` (prod only, must be non-empty)
   - `db_url: str` with URL validation
   - `rate_limit_enabled: bool`
   - All `DOCREVIEW360_*` env vars with types and constraints
2. Call `validate_config()` in `api/__init__.py` at import time
3. In dev mode: log warnings for missing optional config
4. In prod mode: raise `ConfigError` for any invalid required config

Affected Files:
- `src/docreview360/config_validator.py` (new)
- `src/docreview360/api/__init__.py`

---

**R-05: Global Exception Handler Middleware**

Problem:
Unhandled exceptions in request handlers return raw 500 responses with no
trace_id, no structured format, and potentially leak internal details.

Recommendation:
Add a global exception handler that catches all unhandled exceptions, logs them
with trace_id, and returns a safe structured error response.

Implementation:
1. In `api/__init__.py`, add exception handlers for:
   - `AppError` subclasses — return structured `ErrorResponse` with appropriate status
   - `RequestValidationError` — return 422 with field-level details in standard envelope
   - `StarletteHTTPException` — wrap FastAPI default responses in standard envelope
   - `Exception` catch-all — log with trace_id, return safe 500 with `internal_error` code
2. All responses include `trace_id` from correlation ID middleware

Affected Files:
- `src/docreview360/api/__init__.py`

---

#### P1 — Stability Improvements

These tasks reduce fragility and improve maintainability. Strongly recommended
before release; can be done incrementally.

---

**R-06: Input Validation Hardening**

Problem:
Only 86 constraint annotations exist across 364 endpoints. String fields for
names, descriptions, and URLs lack length limits. Numeric fields lack range
constraints. Malformed or oversized inputs could cause unexpected behavior.

Recommendation:
Add systematic input constraints to Pydantic request models and FastAPI
parameter declarations.

Implementation:
1. Audit all `Body()`, `Query()`, `Path()` parameters for missing constraints
2. Add `min_length=1, max_length=255` to name/title fields
3. Add `max_length=10000` to description/content fields
4. Add `ge=0` to pagination parameters (`skip`, `limit`)
5. Add `le=1000` to `limit` parameters to prevent unbounded queries
6. Add URL validation (`HttpUrl`) to all URL input fields
7. Add `constr(pattern=...)` for identifier fields (project IDs, usernames)

Affected Files:
- All router files in `src/docreview360/api/`
- Pydantic models in `_models.py` files across packages

---

**R-07: Decompose Monolithic Router Files**

Problem:
Three router files exceed 1,000 lines each, mixing unrelated concerns. Changes
to one endpoint risk breaking another. Code review is difficult.

Recommendation:
Split each oversized router into focused sub-routers by domain.

Implementation:

`admin_router.py` (1,524 lines, 49 routes) split into:
- `api/system_admin_router.py` — health, cache, rebuild, seed, environments
- `api/settings_router.py` — config, branding, terminology, FSV settings
- `api/plugin_admin_router.py` — builtin status, toggle, marketplace config
- `api/audit_admin_router.py` — audit log review, purge, integrity check

`workflows_router.py` (1,256 lines, 48 routes) split into:
- `api/workflow_templates_router.py` — template CRUD, starter content
- `api/workflow_instances_router.py` — execution, status, listing
- `api/phases_router.py` — phase definitions, SLA, advancement

`tools_router.py` (1,083 lines, 37 routes) split into:
- `api/validation_router.py` — preflight, regulatory, quality checks
- `api/conversion_router.py` — document format conversion
- `api/accessibility_router.py` — accessibility scanning

Backward compatibility: Register split routers in `api/__init__.py` with the
same prefix so URLs don't change.

Affected Files:
- `src/docreview360/api/admin_router.py` → 4 files
- `src/docreview360/api/workflows_router.py` → 3 files
- `src/docreview360/api/tools_router.py` → 3 files
- `src/docreview360/api/__init__.py` (update imports)

---

**R-08: Decompose models.py into Domain Packages**

Problem:
`models.py` (721 lines, 42 SQLAlchemy models) is a single-point-of-change
that every module imports from. Any model change risks cascading effects.

Recommendation:
Split into domain-specific model files with a backward-compatible `__init__.py`.

Implementation:
Create `src/docreview360/models/` package:
- `auth_models.py` — User, APIKey, UserSessionRecord, OIDCStateRecord
- `document_models.py` — Document, DocumentVersion, DocumentBranch, QualityScore
- `workflow_models.py` — Workflow, WorkflowInstanceRecord, WorkflowTemplateRecord
- `approval_models.py` — Approval, ApprovalRecord
- `audit_models.py` — AuditLog, RevokedToken
- `org_models.py` — Organization, OrgConfig, OrgToolConfig
- `__init__.py` — re-export all models for backward compatibility

Affected Files:
- `src/docreview360/models.py` → `src/docreview360/models/` (6 files + init)

---

**R-09: Decompose Frontend Project Page**

Problem:
`pages/projects/[id]/index.tsx` is 3,059 lines containing project overview,
phases, documents, reviewers, feedback, quality scores, and audit timeline.
Hook ordering bugs were already documented in item 49.

Recommendation:
Extract each section into its own component file.

Implementation:
Create `frontend/components/project/`:
- `ProjectPhases.tsx` — phase tabs, SLA, advancement
- `ProjectDocuments.tsx` — document list, upload, quality scores
- `ProjectReviewers.tsx` — reviewer section, assignments, reminders
- `ProjectFeedback.tsx` — feedback ledger, comments, filter chips
- `ProjectAudit.tsx` — audit timeline, notification log
- `ProjectOverview.tsx` — title, description, owner, status

Each component receives props or uses the shared `useProject` hook.

Affected Files:
- `frontend/pages/projects/[id]/index.tsx` (reduce to ~500 lines of composition)
- `frontend/components/project/` (6 new files)

---

**R-10: Activate Dependabot**

Problem:
`.github/dependabot.yml` exists but has an empty updates section. Dependency
vulnerabilities will not be surfaced automatically.

Recommendation:
Configure Dependabot for both pip and npm ecosystems.

Implementation:
Update `.github/dependabot.yml` with update rules for pip (root `/`),
npm (`/frontend`), and github-actions (`/`), all on weekly schedule with
10/10/5 open PR limits respectively.

Affected Files:
- `.github/dependabot.yml`

---

**R-11: Standardize Retry Policy**

Problem:
Retry logic is implemented manually in `event_dispatcher.py` and
`approvals/signatures.py` with different patterns. No shared utility exists.

Recommendation:
Create a shared retry utility or adopt `tenacity` for consistent retry behavior.

Implementation:
1. Create `src/docreview360/retry.py` with:
   - `RetryPolicy(max_attempts, base_delay, max_delay, jitter)`
   - `retry_with_backoff(func, policy)` — sync wrapper
   - `async_retry_with_backoff(func, policy)` — async wrapper
   - Logging on each retry attempt with attempt number and delay
2. Migrate `event_dispatcher.py` and `signatures.py` to use the shared utility
3. Document retry behavior in error responses (`Retry-After` header)

Affected Files:
- `src/docreview360/retry.py` (new)
- `src/docreview360/event_dispatcher.py`
- `src/docreview360/approvals/signatures.py`

---

**R-12: Add Exception Logging to Silent Catch Blocks**

Problem:
56% of exception handlers (156 of 314) have no logging. While many are
intentionally defensive, some in `notifications.py`, `sod.py`, and
`event_dispatcher.py` should at least log at DEBUG or WARNING level.

Recommendation:
Add structured logging to all exception handlers that currently pass silently.

Implementation:
1. Grep for `except.*:\s*(pass|return|continue)` patterns
2. For each, determine if it's:
   - **Intentionally silent** (e.g., feature detection `try: import X`) — add comment
   - **Defensively silent** (e.g., notification fallback) — add `logger.debug()`
   - **Incorrectly silent** (e.g., data corruption risk) — add `logger.warning()`
3. Never convert to `logger.error()` unless it represents a real failure

Affected Files:
- `src/docreview360/notifications.py`
- `src/docreview360/sod.py`
- `src/docreview360/event_dispatcher.py`
- ~20 other modules with silent catches

---

**R-13: Typed Response Models for Admin Endpoints**

Problem:
20+ admin endpoints return `dict[str, Any]` without response models. Clients
cannot validate response shapes; Swagger docs show no schema.

Recommendation:
Create Pydantic response models for all admin endpoints that currently return
raw dicts.

Implementation:
1. Identify all endpoints returning `dict[str, Any]` or untyped dicts
2. Create response models in `src/docreview360/api/schemas/admin_schemas.py`:
   - `RBACMatrixResponse`, `EnvironmentListResponse`, `SettingsResponse`,
     `AuditCheckResponse`, `BrandingResponse`, etc.
3. Add `response_model=` to endpoint decorators
4. FastAPI will enforce shape validation on all responses

Affected Files:
- `src/docreview360/api/schemas/` (new directory)
- `src/docreview360/api/admin_router.py`
- Other routers returning untyped dicts

---

#### P2 — Long-term Hardening

These tasks are engineering improvements that reduce long-term maintenance burden
and improve the developer experience.

---

**R-14: Service Layer Abstraction**

Problem:
Business logic is scattered across routers and utility functions with no
intermediate service layer. Routers directly call `add_project()`,
`list_projects()`, etc. This makes testing harder (must use full HTTP client)
and business logic harder to find.

Recommendation:
Introduce service classes that encapsulate business logic between routers and
data access.

Implementation:
Create `src/docreview360/services/`:
- `project_service.py` — `ProjectService(create, list, update, delete, advance_phase)`
- `document_service.py` — `DocumentService(create, upload, convert, version, freeze)`
- `workflow_service.py` — `WorkflowService(create_template, execute, get_status)`
- `review_service.py` — `ReviewService(assign, submit, concur, remind, export)`

Routers call service methods instead of directly calling utility functions.
Services are injected via FastAPI `Depends()`.

Affected Files:
- `src/docreview360/services/` (new package)
- All router files (incremental migration)

---

**R-15: Property-Based Testing for Edge Cases**

Problem:
Only 8 parametrized tests exist. Edge cases (unicode, max-length strings,
boundary values, malformed JSON) are not systematically tested.

Recommendation:
Add Hypothesis-based property tests for critical Pydantic models and utility
functions.

Implementation:
1. Add `hypothesis` to `[test]` extras in `pyproject.toml`
2. Create `tests/property/test_models_property.py`:
   - Generate random `ProjectCreate`, `DocumentModel`, `WorkflowTemplatePayload`
   - Verify serialization round-trips (`model.model_dump()` -> `Model(**data)`)
   - Verify constraint enforcement (rejected inputs don't crash)
3. Create `tests/property/test_crypto_property.py`:
   - Encrypt/decrypt round-trip with random payloads
   - Verify nonce uniqueness
4. Create `tests/property/test_search_property.py`:
   - Index random documents, verify they're findable

Affected Files:
- `pyproject.toml` (add hypothesis dep)
- `tests/property/` (3 new test files)

---

**R-16: CI Coverage Enforcement per Module**

Problem:
The 90% branch coverage gate is global. Individual modules can have 0% coverage
without failing CI if other modules compensate.

Recommendation:
Add per-module coverage tracking that flags modules below threshold.

Implementation:
1. Create `scripts/coverage-by-module.py`:
   - Parse `coverage.json` output
   - Report per-module branch coverage
   - Flag modules below 80% with file paths
   - Exit non-zero if any critical module is below threshold
2. Add to CI pipeline as a reporting step (not blocking initially)
3. Gradually raise thresholds as tests are added

Affected Files:
- `scripts/coverage-by-module.py` (new)
- `.github/workflows/ci.yml`

---

**R-17: Frontend API Client Consolidation**

Problem:
Both `frontend/lib/api.ts` and `frontend/lib/apiProxy.ts` exist. `apiProxy.ts`
is marked deprecated but still present, creating confusion about which client
to use.

Recommendation:
Remove the deprecated `apiProxy.ts` and ensure all code uses `api.ts`.

Implementation:
1. Grep for imports of `apiProxy` across all frontend files
2. Migrate any remaining usages to `api.ts`
3. Delete `frontend/lib/apiProxy.ts`
4. Add a lint rule preventing future imports from deprecated modules

Affected Files:
- `frontend/lib/apiProxy.ts` (delete)
- Any files importing from `apiProxy`

---

**R-18: Metrics Endpoint for Prometheus Scraping**

Problem:
`monitoring.py` defines Prometheus counters and histograms but there is no
`/metrics` endpoint in the app for Prometheus to scrape directly.

Recommendation:
Add a `/metrics` endpoint that Prometheus can scrape.

Implementation:
1. Expose metrics via `prometheus_client.generate_latest()` at `GET /metrics`
2. Gate behind `DOCREVIEW360_METRICS_ENABLED` env var
3. Exclude from auth requirements (or use a separate metrics token)
4. Add default request duration, status code, and path labels

Affected Files:
- `src/docreview360/api/__init__.py`
- `src/docreview360/monitoring.py`

---

**R-19: Database Migration Safety**

Problem:
Alembic is set up but migrations are a single baseline file. As the schema
evolves, migration safety (reversibility, data preservation) becomes critical.

Recommendation:
Establish migration safety practices.

Implementation:
1. Add `scripts/check-migration-safety.py`:
   - Verify all migrations have `downgrade()` functions
   - Check for destructive operations (DROP TABLE, DROP COLUMN) and flag them
   - Verify migration chain is linear (no forks)
2. Add a CI step that runs `alembic check` to verify head is current
3. Document migration testing process in `docs/migrations.md`

Affected Files:
- `scripts/check-migration-safety.py` (new)
- `alembic/` (verify existing migrations)
- `.github/workflows/ci.yml`

---

**R-20: WebSocket Authentication**

Problem:
The `/ws/dashboard` WebSocket endpoint accepts an unvalidated `?user=` query
parameter. Any client can impersonate any user on the WebSocket connection.

Recommendation:
Validate JWT tokens on WebSocket connections before accepting them.

Implementation:
1. Change `/ws/dashboard` to accept `?token=<jwt>` instead of `?user=`
2. Validate the JWT using the existing `auth.decode_token()` function
3. Reject connections with invalid or expired tokens (close code 4001)
4. Extract username from the validated token claims

Affected Files:
- `src/docreview360/api/__init__.py` (WebSocket endpoint)
- Frontend WebSocket connection code

---

### Production Readiness Checklist

Before any production deployment, verify:

- [ ] All P0 tasks from this plan are implemented
- [ ] `pytest -q` passes with 0 failures (not just "passes in isolation")
- [ ] `pytest --cov=src --cov-branch --cov-fail-under=90` passes
- [ ] `mypy --strict src` passes (excluding documented exclusions)
- [ ] `ruff check src` passes with 0 errors
- [ ] `bandit -r src -lll --skip B101` passes with 0 issues
- [ ] `python scripts/run-pip-audit.py` reports 0 critical/high vulnerabilities
- [ ] `npm audit --production` in `frontend/` reports 0 critical vulnerabilities
- [ ] Configuration validation passes for production env vars
- [ ] Health endpoints (`/health/live`, `/health/ready`) return 200
- [ ] Error responses follow the unified `ErrorResponse` contract
- [ ] All critical workflows have E2E test coverage:
  - Login -> create project -> upload document -> assign reviewer -> submit review -> sign -> close
- [ ] Rollback strategy documented (database migration down, container rollback)
- [ ] Structured logging verified in production log output
- [ ] Rate limiting verified with load test
- [ ] CORS configuration verified against production frontend origin
- [ ] Secret key rotation tested (previous key acceptance window)
- [ ] Backup/restore tested (`scripts/db_backup.sh` round-trip)

---

- [ ] Confirm `docreview360 init` is updated with the latest software applications.
- [x] The login page shows "login.title", "login.username", "login.password", "login.submit". Why are all beginning with "login."?
  Fixed by adding a public locale-bundle fallback in `frontend/lib/useTranslation.ts`
  so logged-out pages no longer depend on the authenticated i18n API. Verified in
  `tests/test_release_checklist_user_fixes.py`. (Completed 2026-03-17)
- [x] In Projects, I see "projects.new", "dashboard.assigned", "dashboard.in_progress", "dashboard.completed", "dashboard.overdue". What do they have the prefix (projects. or dashboard.)?
  Same root cause as the login-page issue above; fixed by the public locale fallback
  for unauthenticated translation loading. Verified in
  `tests/test_release_checklist_user_fixes.py`. (Completed 2026-03-17)
- [x] In demo-project, i have bob assigned to review. however, the Assigned dashboard and Pending dashboard show 0 (zero). If we have someone/user in the reviewer sign-off & concurrence, shouldn't the dashboards identify the correct number?
  Fixed backend project/dashboard scoping so active reviewer assignments now count
  for project visibility and dashboard widget totals even before a workflow approval
  record exists. Verified in `tests/test_release_checklist_user_fixes.py` and
  `tests/test_user_scoped_dashboards.py`. (Completed 2026-03-17)
- [x] In Admin Dashboard, in User Roles Breakdown, what is "3 perms", "7 perms", etc.? What's "perms"?
  Updated the admin dashboard copy to spell out `permissions` instead of `perms`.
  Verified in `tests/test_release_checklist_user_fixes.py`. (Completed 2026-03-17)
- [x] In Admin Dashboard, I added users to review and made other updates in prjects, but the audit log feed and active users are empty. Are these dashboard wired into the system?
  Wired the admin dashboard to load recent audit activity and derive active-user data
  from audit/user endpoints instead of leaving those panels hardcoded empty. Verified
  by source-level guard in `tests/test_release_checklist_user_fixes.py`.
  (Completed 2026-03-17)
- [x] I don't understand prject view. We invite a review (there's another window indicating reviewer signoff & concurrence, which appears to duplicate reviewer table), then there's the Approvals table. Is this saying that a reviewer might not be an approver? If so, that's fine. However, I added a reviewer and when i tried to add that same reviewer to the approvals table, I got "Reviewer must be assigned to the project first." I thought I did that. Maybe more onscreen text would help clarify the flow (ensure that it's ready for localization too)
  Added explanatory onscreen copy distinguishing reviewer assignments, reviewer
  sign-off/concurrence, and phase approvals. Also changed approval creation to accept
  invited reviewers from assignment data instead of only the legacy reviewer list.
  Verified in `tests/test_release_checklist_user_fixes.py`. (Completed 2026-03-17)
- [x] In Document Checker, I tried to select a system document, but received Could not fetch documents: HTTP 401: Unauthorized. Why is this? Should any access level be able to do this? With this, we need to ensure that the document naming (for example if a TipTap document) is clear so that if we have a list of documents, we can find it easily
  Added fallback to `GET /documents/public` when private document listing is not
  authorized, with a note that sign-in is still required for private project
  documents. Also improved document labels to show project/type/editor/status context.
  Verified in `tests/test_release_checklist_user_fixes.py`. (Completed 2026-03-17)
