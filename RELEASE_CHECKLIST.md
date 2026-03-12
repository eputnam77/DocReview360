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
  `GET /document-types/{name}/starter-content` is live and covered by
  `tests/test_item44_review_cycle.py`, and `frontend/__tests__/starterContent.test.ts`
  now exists, but the missing requirement is executable frontend regression
  coverage: `npm test` currently fails during Vitest startup (`ERR_REQUIRE_ESM`
  from `frontend/vitest.config.ts`) under Node `18.20.4`, while the installed
  `vite@7.3.1` requires Node `^20.19.0 || >=22.12.0`. Fix the frontend
  Vitest/Node compatibility and rerun the starter-content test before moving
  this out. (2026-03-12 verification)

### 13) Scope and release targets

- [ ] Define supported platforms and document them. `docs/supported-platforms.md`
  exists, but the missing requirement is an accurate frontend Node support
  matrix: it still marks Node 18.x as supported even though the installed
  frontend toolchain (`vite@7.3.1`) requires Node `^20.19.0 || >=22.12.0`, and
  `npm test` fails on Node `18.20.4`. Align the documented support table with
  the actual toolchain requirements before moving this out. (2026-03-12 verification)
- [ ] Freeze feature scope. Fixes only after this checkpoint.
- [ ] Create a release branch and protect `main`.

### 14) Repository hygiene and public readiness

- [ ] Run a secret scan on the full history and working tree.
- [ ] Remove or rotate any hardcoded tokens, test credentials, or sample secrets.
- [ ] Remove unnecessary files and stale artifacts before release.
- [ ] Ensure all `example.com` and placeholder URLs or emails are updated.
  Missing requirement: tracked public-facing placeholders still remain, including
  `frontend/pages/docs/index.tsx` (`https://example.com/docreview360/`) and
  `helm/docreview360/Chart.yaml` (`info@example.com`). Remove or replace those
  remaining placeholders before moving this out. (2026-03-12 verification)

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
  Missing requirement: tracked public-facing placeholders still remain in
  `frontend/pages/docs/index.tsx` and `helm/docreview360/Chart.yaml`. (2026-03-12 verification)
- [ ] Update docs and metadata that still mention GPL or placeholder contact data.
  Missing requirement: stale generated metadata still remains in
  `src/docreview360.egg-info/PKG-INFO`, which still advertises
  `info@example.com`, `GPL-3.0-only`, and GPL classifiers. Remove or regenerate
  that stale metadata before moving this out. (2026-03-12 verification)
- [ ] Review references to private repositories and remove or clearly mark them as optional.
- [ ] Confirm branch protection, issue tracker settings, security reporting, and Actions
  settings are ready for a public repository.

### 16) Documentation and user experience

- [ ] Ensure `README.md` matches `.dev/AGENTS.md` structure requirements.
  Missing requirement: README still contradicts `.dev/AGENTS.md` in the setup
  instructions. The README says `# 2. Create and activate venv (Python 3.13)`
  while `.dev/AGENTS.md` documents Python 3.11-3.12 support and says Python 3.13
  is not supported. Align the README before moving this out. (2026-03-12 verification)
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

2026-03-12 verification note: the frontend items in this section remain open
until the Vitest suite is runnable again. `npm test` currently fails during
startup (`ERR_REQUIRE_ESM` from `frontend/vitest.config.ts`) under Node
`18.20.4`, while the installed `vite@7.3.1` requires Node
`^20.19.0 || >=22.12.0`.

- [ ] Finish migrating active frontend shared hooks, components, state, and
  utility code off `authenticatedFetch(\`${API}/...\`)` and raw `fetch(\`${API}/...\`)`.
  Added `frontend/__tests__/brandingStore.test.ts` — 15 tests covering
  `state/branding.ts` end-to-end (source guard, fetch URL contract, store population,
  error fallback, idempotency). Script exits 0 confirming migration complete. (2026-03-12)
- [ ] Broaden the frontend raw-fetch guard: `scripts/check-api-fetch-pattern.mjs`
  and `lint:api-fetch` exist. Added `frontend/__tests__/checkApiFetchPattern.test.ts`
  — 10 tests covering clean-pass, violation detection in all 5 scan dirs,
  login.tsx exemption, and relative-path allowance. (2026-03-12)

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

2026-03-12 verification note: the frontend items below remain open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suites are rerun.

**Phase 2 — Multi-channel notification for review events**

The verified notification-preference work was moved to
`docs/latest_features.md` on 2026-03-12.

**Phase 5 — Reviewer experience (what the reviewer sees)**

- [ ] Read-only document preview panel alongside the feedback table (deferred)

**Phase 6 — Project view layout and navigation**

- [ ] Collapsible document preview panel on the right side of Feedback/Signatures tabs (deferred)

**Phase 7 — Records retention and project close-out**

- [ ] Wire NARA metadata to project API: Added `frontend/__tests__/naraAndSlaPanel.test.ts`
  — source-level tests covering state declarations, API load from project data, save
  payload shape (4 fields + PUT), success/error toasts. (2026-03-12)

**Phase 8 — Deadline and SLA tracking**

- [ ] Expose default review SLA configuration in the admin UI. SLA endpoints
  and query wiring covered in `frontend/__tests__/naraAndSlaPanel.test.ts`
  — 6 tests for sla-summary, sla-deadlines, run-sla-reminders, conditional render,
  and query key shape. (2026-03-12)

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
  the new Feedback tab. Added source guards in `frontend/__tests__/reviewCycleHook.test.ts`
  — redirect to `#feedback`, router.isReady guard, id guard, loading skeleton. (2026-03-12)
- [ ] Keep the existing `useApprovals`, `useComments`, `useProjectReviewers`
  hooks but compose them under a new `useReviewCycle(projectId)` hook.
  Added 30 tests in `frontend/__tests__/reviewCycleHook.test.ts` covering interface,
  composition, and derived-field pure logic. (2026-03-12)

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
2026-03-12 verification note: the frontend/UI items below remain open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suites are rerun.

- [ ] Add sidebar panel showing live FSV validation summary and overall score.
  `frontend/__tests__/fsvEditorAndProject.test.ts` covers Validation Summary
  section: score, grade, issue_count, source, color thresholds, conditional
  render after save. (2026-03-12)
- [ ] Configure FSV endpoint URL in the editor plugin via DocReview360's
  settings API. Created `frontend/__tests__/fsvUrlSettings.test.ts` — 21 tests:
  tools page loads FSV URL from `GET /admin/settings/fsv-url`, saves via `PUT` with
  `{url}` body, input state management, disabled-when-unchanged guard, FEDERAL_STYLE_VALIDATOR_URL
  env var reference, editor uses `/documents/preflight` (not FSV directly), `get_fsv_url()`
  env→settings fallback chain, `is_fsv_configured()` export, admin-only guard. (2026-03-12)

**Phase 3 — UX consistency and on-save validation**

The FSV experience must be identical whether running standalone in a browser or
inside DocReview360 under Tools. This establishes a consistent brand.

- [ ] Ensure the `/tools/checker` page renders FSV results using the same visual
  layout, color scheme, and severity icons. The current implementation is only
  partially verified; the checklist itself still notes parity is pending FSV's
  published design tokens. Add screenshot or UI regression coverage once the
  target tokens are defined.
- [ ] Add on-save validation. `frontend/__tests__/fsvEditorAndProject.test.ts`
  — 9 tests: POST to `/documents/preflight`, `document_id` in body,
  `autoValidationEnabled` gate, fire-and-forget `.catch`, `setValidationSummary`
  called with score/grade/issue_count/source. (2026-03-12)
- [ ] Display minimal FSV feedback in the editor toolbar. `fsvEditorAndProject.test.ts`
  — 7 tests: score %, grade, issue_count, source, color thresholds, conditional
  render, toolbar panel presence. (2026-03-12)
- [ ] Quality badge added next to "Edit Document" CTA in **Project View**.
  `fsvEditorAndProject.test.ts` — 5 tests: fsvEnabled gate, quality_score %,
  plain_language_grade, color coding (green/amber/red), null guard. (2026-03-12)
- [ ] Make on-save validation configurable. `fsvEditorAndProject.test.ts`
  verifies tools page fetches auto-validation state, editor reads it on mount,
  `toggleAutoValidation` PUT flow. (2026-03-12)

**Phase 4 — Core Tool Pack designation**

FSV is the Core Tool Pack for DocReview360 — enabled by default for all orgs.

- [ ] Designate FSV as the "Core" tool in the plugin marketplace. `fsvEditorAndProject.test.ts`
  verifies `isCore: true` on FSV entry, `CoreBadge` renders for core tools.
  (2026-03-12)
- [ ] Administrators can disable FSV in Tools page. `fsvEditorAndProject.test.ts`
  confirms `isBuiltIn` + `togglePlugin` wiring for the FSV-specific toggle.
  (2026-03-12)
- [ ] When FSV is disabled, hide FSV-specific UI. `fsvEditorAndProject.test.ts`
  confirms `fsvEnabled` gate guards quality badge and quality table in project
  view. (2026-03-12)

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

2026-03-12 verification note: the frontend items below remain open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suites are rerun.

- [ ] Add offline editing support. Added `frontend/__tests__/offlineStorage.test.ts`
  — 13 tests covering saveOfflineDraft, loadOfflineDraft, markSynced, getPendingDrafts,
  and clearDraft via the localStorage fallback path (used in jsdom and private browsing).
  (2026-03-12)
The verified format-fidelity expansion (RTF, ODT, EPUB, LaTeX, and Confluence
wiki markup) was moved to `docs/latest_features.md` on 2026-03-12.

**Phase 3 — Enterprise search and analytics**

The verified external-search stub and analytics dashboard/export endpoints were
moved to `docs/latest_features.md` on 2026-03-12.

### 42) Configuration and extensibility

2026-03-12 verification note: the frontend item below remains open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suite is rerun.

- [ ] Add theme and white-label support. Added `frontend/__tests__/useTheme.test.ts`
  — 10 tests covering CSS custom property injection for all 4 branding color
  variables and removal when null. (2026-03-12)

### 45) Role-based dashboard UX improvements

Dashboards exist for User, Manager, and Admin roles with proper RBAC enforcement
and per-widget visibility customization. The following items improve discoverability
and role-appropriate navigation.

2026-03-12 verification note: the frontend items below remain open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suites are rerun.

- [ ] Add a **settings cog icon** to each dashboard header (User, Manager,
  Admin). Added `frontend/__tests__/dashboardAndSidebar.test.ts` — 4 tests
  confirming customize/settings action across all 3 dashboard variants. (2026-03-12)
- [ ] Gate dashboard links in the sidebar by role. Source-level tests in
  `dashboardAndSidebar.test.ts` verify isAdmin read, roles read, dashboardNav
  role-based selection, and isAdmin-gated admin sections. (2026-03-12)
- [ ] Persist widget visibility preferences to SQLite. Frontend tests in
  `dashboardAndSidebar.test.ts` cover state/visibility.ts API endpoint, PUT
  method, authenticatedFetch usage, and settings.tsx UI contract. (2026-03-12)

### 46) Frontend localization readiness

Backend i18n infrastructure is complete (`i18n.py`, 70 keys, 4 locales, REST
endpoints). Frontend locale JSON files exist in `public/locales/`. Next.js i18n
routing is configured. However, **zero frontend components use the i18n system** —
all UI strings are hardcoded in English.

**Phase 1 — Hook and switcher**

2026-03-12 verification note: the frontend items below remain open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suites are rerun.

- [ ] Created `frontend/lib/useTranslation.ts` hook. Added `frontend/__tests__/useTranslation.test.ts`
  — 24 tests covering `_dotGet`, `_buildNested`, t() resolution chain, locale persistence,
  and URL routing for translations vs. terminology. (2026-03-12)
- [ ] Created `frontend/components/LocaleSwitcher.tsx` dropdown with 4 locales.
  Added `frontend/__tests__/LocaleSwitcher.test.tsx` — 5 tests covering render,
  selection state, and setLocale call contract. (2026-03-12)
The verified backend locale-preference endpoints were moved to
`docs/latest_features.md` on 2026-03-12.

**Phase 2 — String extraction and migration**

- [ ] Extract hardcoded UI strings from `login.tsx`, `projects/index.tsx`, and
  `dashboard/user.tsx`. Pages confirmed to use `useTranslation` + `t()` calls.
  `helpAndSidebar.test.ts` verifies locale keys exist in all 4 locale files.
  (2026-03-12)
- [ ] Replace hardcoded strings with `t("key")` calls in `login.tsx`,
  `projects/index.tsx`, and `dashboard/user.tsx`. Source-level verification in
  `frontend/__tests__/helpAndSidebar.test.ts` — 6 tests across 4 locales.
  (2026-03-12)
- [ ] `LocaleSwitcher` added to sidebar footer. Sidebar source confirmed to
  include `LocaleSwitcher`; `helpAndSidebar.test.ts` asserts the import.
  (2026-03-12)

**Phase 3 — Full coverage**

- [ ] Migrate remaining pages and components to use `useTranslation`. Source
  assertions in `frontend/__tests__/i18nPhase3.test.ts` confirm `search.tsx`,
  `configuration/index.tsx`, and `profile.tsx` import and use `useTranslation`.
  (2026-03-12)
- [ ] Added `frontend/scripts/check-hardcoded-strings.mjs` lint script
  (`npm run lint:i18n`). `i18nPhase3.test.ts` verifies: script exits 0,
  emits [i18n-lint] output, detects JSX text and attribute violations, skips
  t()-wrapped lines, and scans `pages/` + `components/`. (2026-03-12)
- [ ] Branding/terminology overrides now applied on top of locale translations
  via `GET /i18n/terminology/{locale}?org_id=`. `i18nPhase3.test.ts` — 7 source
  tests confirm orgId URL construction, separate query key, cache invalidation,
  and graceful fallback. (2026-03-12)

### 47) In-app support and documentation

A "Support" link exists in the sidebar and the footer shows configurable
Support/Docs/Security/Privacy links via the branding system. However, the actual
help and documentation pages are stubs.

2026-03-12 verification note: the frontend items below remain open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suites are rerun.

- [ ] Replaced `/docs/` placeholder with real in-app help. Five-tab layout now
  covered by `frontend/__tests__/helpAndSidebar.test.ts` — Getting Started,
  Key Concepts, FAQ, Keyboard Shortcuts, and API Reference tabs verified.
  (2026-03-12)
- [ ] Flesh out `/help` content. `helpAndSidebar.test.ts` verifies key-concepts,
  FAQ items (FAQ_ITEMS constant + `q:` entries), keyboard-shortcut section, and
  API Reference section. (2026-03-12)
- [ ] Sidebar "Support" link replaced with collapsible "Help & Support"
  section. `helpAndSidebar.test.ts` asserts label text, `/help#getting-started`
  link, and `/help#shortcuts` link. (2026-03-12)
- [ ] Added `HelpTooltip` component with popover. `helpAndSidebar.test.ts`
  verifies component file exists and renders a Popover/Tooltip element.
  (2026-03-12)
- [ ] Wire `brandingSupportUrl` and `brandingDocsUrl`. `helpAndSidebar.test.ts`
  verifies sidebar reads both branding URLs and uses `brandingDocsUrl` in an
  href. (2026-03-12)

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

2026-03-12 backend verification note: `tests/test_item48_validate.py` currently
fails because `GET /admin/settings/fsv-checks` returns `passive_voice: false`
from `settings.yaml`, so the validation-endpoint/default-settings work below is
not fully verified yet.

- [ ] Consolidated three separate validation endpoints into
  `POST /documents/validate`. Added `tests/test_item48_validate.py` — 22 tests
  covering endpoint contract, selective check execution, authentication,
  and per-category FSV settings persistence. (2026-03-12)

**Tool configurability**

- [ ] Add per-check granularity for FSV rules in the admin Configuration →
  Tools page. Category persistence tested in `tests/test_item48_validate.py`
  (GET/PUT /admin/settings/fsv-checks round-trip). (2026-03-12)
2026-03-12 verification note: the frontend tools-index item below remains open
until the same Vitest/Node compatibility blocker from item 43d is fixed and the
cited frontend suite is rerun.

- [ ] Tools index page now shows Active/Disabled/Not-installed status badges,
  community labels, dimmed disabled cards, admin-only Configure links, and
  Enable/Disable toggles for built-in plugins. Added
  `frontend/__tests__/toolsIndexPage.test.ts` — 24 tests covering all states,
  gating logic, toggle endpoint wiring, and getStatus return values. (2026-03-12)

### 49) Frontend stability — React hook violations and stale crashes

Pages crash in production with "Rendered more hooks than during the previous
render" or "Rendered fewer hooks than expected". The root cause is React's Rules
of Hooks being violated: hooks must be called in the **same order on every
render** and **never after a conditional return**. Tests miss this because Jest +
Testing Library hydrate synchronously and never hit the loading/null states that
trigger early returns. The "stale" message users see is React or Next.js
detecting that the previous render's hook count differs from the current one.

**Regression coverage still required**

2026-03-12 verification note: the frontend items below remain open until the
same Vitest/Node compatibility blocker from item 43d is fixed and the cited
frontend suites are rerun.

- [ ] `pages/projects/[id]/index.tsx`: Added `frontend/__tests__/hookOrderRegression.test.ts`
  source-level regression guard confirming `feedbackShowMyOnly` is declared before
  conditional early returns. (2026-03-12)

- [ ] **`router.isReady` guard added** to the affected dynamic pages. Source-level
  test in `hookOrderRegression.test.ts` verifies the guard is present and
  `router.query.id` is not accessed without it. (2026-03-12)

- [ ] **Stale closures fixed** in `pages/projects/[id]/index.tsx`. Addressed via
  source-level assertions in `hookOrderRegression.test.ts`; dependency-array
  changes are present in code. (2026-03-12)

- [ ] **React Error Boundary added**. Added `frontend/__tests__/PageErrorBoundary.test.tsx`
  — 7 tests covering fallback UI, error display, Try-again reset, and
  resetKey-based route-change auto-reset. (2026-03-12)

- [ ] **`useApprovals` `any` type removed**. `RawApproval` and `mapApproval` verified
  in `hookOrderRegression.test.ts` — interface definition, mapper usage, field
  types, and state cast confirmed. (2026-03-12)

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
  Full MSW delayed-response tests deferred until `msw` is added as dev dep. (2026-03-12)
