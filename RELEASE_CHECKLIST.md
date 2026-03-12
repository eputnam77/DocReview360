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
  `tests/test_item44_review_cycle.py`, but the audit found no automated
  frontend test proving `frontend/pages/editors/tiptap.tsx` loads starter
  content first and falls back to `/templates` on 404 or error. Add that
  editor regression coverage before moving this out of the checklist.

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
- [ ] Local "release shepherd" loop: `scripts/release-shepherd.sh` exists, but
  the audit found no dedicated automated tests for lockfile behavior,
  first-unchecked-item selection, or report contents under
  `artifacts/automation/`. Add script coverage and a sample artifact assertion
  before moving it out of the checklist.
- [ ] Require artifact-based state for every autonomous run: prompt text, selected files, commands run, exit codes, test results, diff summary, and stop reason under `artifacts/automation/`.
- [ ] Define hard AI guardrails before any autonomous loop: approved model list, max turns, max tokens, retry limit, fallback model, writable path allowlist, and mandatory human review for high-risk files.
- [ ] Add a lockfile or lease so only 1 automation loop edits the repo at a time.
- [ ] Add a watchdog that stops the loop after repeated no-op diffs, repeated failing tests, or budget exhaustion.
- [ ] Prototype a Raspberry Pi-friendly runner for headless loops with a shell wrapper, lockfile, and append-only logs instead of relying on `cron` or `systemd`.
- [ ] Custom Claude Code commands: `.claude/commands/triage-failure.md`,
  `docs-drift.md`, `checklist-next.md`, `packaging-audit.md` exist, but there
  is no automated smoke coverage that command discovery and rendering still
  work. Add a verification step or test harness before moving them out of the
  checklist.
- [ ] Use Claude Code hooks to enforce "read tests first" and "run verification before write" for autonomous maintenance commands.
- [ ] Build a failing-test triage loop that watches `pytest`, Playwright, and E2E failures, clusters similar stack traces, drafts the likely root cause, and proposes the smallest patch.
- [ ] Build a flaky-test hunter that reruns smoke tests multiple times, captures artifacts, and ranks failures by frequency and first bad commit if git history is available.
- [ ] Docs drift checker: `scripts/check-docs-drift.py` exists, but the audit
  found no tests covering representative drift detection, exit codes, or
  false-positive handling. Add script-level tests before moving it out of the
  checklist.
- [ ] Build a packaging auditor that inspects wheel, sdist, and Docker contents and flags shipped tests, placeholders, internal files, or runtime junk before release.
- [ ] Placeholder and metadata reviewer: `scripts/check-placeholders.py`
  exists, but the audit found no tests covering scan scope, allowlist behavior,
  or nonzero-exit behavior on findings. Add script-level tests before moving it
  out of the checklist.
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

- [ ] Finish migrating active frontend shared hooks, components, state, and
  utility code off `authenticatedFetch(\`${API}/...\`)` and raw
  `fetch(\`${API}/...\`)`. The code changes are present and
  `tests/test_release_checklist_auth_and_frontend.py` contains static source
  assertions for related fetch cleanup, but the audit found no targeted test
  that exercises the claimed 14-file migration set or the `branding.ts` path
  end to end. Add guard tests or a violating fixture before moving this item.
- [ ] Broaden the frontend raw-fetch guard: `scripts/check-api-fetch-pattern.mjs`
  and `lint:api-fetch` exist, but the audit found no automated proof that the
  guard scans all intended frontend directories and fails on a violating
  fixture. Add a script test and CI invocation before moving this item.

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

- [ ] Notification channel selection per reviewer preference. The model,
  endpoints, and routing logic exist, but `tests/test_item44_notification_prefs.py`
  currently fails in the audited tree: `GET /notifications/preferences/me`
  returned `preferred_channel="in_app"` for `alice` where the suite expects the
  default `email`. Isolate notification-preference state in tests and confirm
  the intended default before moving this item.

**Phase 5 — Reviewer experience (what the reviewer sees)**

- [ ] Read-only document preview panel alongside the feedback table (deferred)

**Phase 6 — Project view layout and navigation**

- [ ] Collapsible document preview panel on the right side of Feedback/Signatures tabs (deferred)

**Phase 7 — Records retention and project close-out**

- [ ] Wire NARA metadata to project API: backend models and endpoints are
  covered by `tests/test_item44_nara.py`, but the audit found no automated
  frontend coverage for the Overview-tab NARA card edit/save round trip. Add
  UI/API round-trip coverage before moving this item.

**Phase 8 — Deadline and SLA tracking**

- [ ] Expose default review SLA configuration in the admin UI. Backend SLA
  logic and endpoints are covered by `tests/test_item44_phase78.py`, but the
  audit found no automated coverage for `SLAPanel` render/edit/save behavior in
  the admin UI. Add that UI coverage before moving this item.

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
  the new Feedback tab. The redirect code is present, but the audit found no
  automated frontend test for the redirect to `/projects/[id]#feedback` or
  parity with the Feedback-tab experience.
- [ ] Keep the existing `useApprovals`, `useComments`, `useProjectReviewers`
  hooks but compose them under a new `useReviewCycle(projectId)` hook.
  `frontend/lib/useReviewCycle.ts` exists, but there is no dedicated hook or
  page integration test covering its composition contract.

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
- [ ] Add sidebar panel showing live FSV validation summary and overall score.
  The editor/sidebar code is present, but the audit found no automated
  frontend coverage that renders the summary after a save cycle.
- [ ] Configure FSV endpoint URL in the editor plugin via DocReview360's
  settings API. The settings endpoints and Tools UI exist, but the audit found
  no targeted test for settings round-trip plus editor consumption.

**Phase 3 — UX consistency and on-save validation**

The FSV experience must be identical whether running standalone in a browser or
inside DocReview360 under Tools. This establishes a consistent brand.

- [ ] Ensure the `/tools/checker` page renders FSV results using the same visual
  layout, color scheme, and severity icons. The current implementation is only
  partially verified; the checklist itself still notes parity is pending FSV's
  published design tokens. Add screenshot or UI regression coverage once the
  target tokens are defined.
- [ ] Add on-save validation. The code is present, but the audit found no
  automated save-cycle test proving the editor posts preflight after save and
  persists the `document_id` path.
- [ ] Display minimal FSV feedback in the editor toolbar. No automated coverage
  was found for the post-save toolbar pill and tooltip state.
- [ ] Quality badge added next to "Edit Document" CTA in **Project View**.
  No automated project-view coverage was found for badge rendering and gating.
- [ ] Make on-save validation configurable. The settings endpoint and Tools UI
  exist, but there is no targeted test for admin toggle persistence and the
  resulting editor behavior change.

**Phase 4 — Core Tool Pack designation**

FSV is the Core Tool Pack for DocReview360 — enabled by default for all orgs.

- [ ] Designate FSV as the "Core" tool in the plugin marketplace. Backend
  metadata and UI badges exist, but there is no automated marketplace test
  asserting core ordering and badge rendering for FSV.
- [ ] Administrators can disable FSV in Tools page. Built-in toggle
  persistence is tested separately, but the audit found no targeted Tools-page
  test for the FSV-specific disable flow.
- [ ] When FSV is disabled, hide FSV-specific UI. No automated coverage was
  found for quality-table and project-badge gating when FSV is off.

**Phase 5 — Full cutover and documentation**

- [ ] Confirm no remaining duplicate style/quality logic in DocReview360 source.
- [ ] Document integration points, config, and FSV version requirements in
  `docs/federal-style-validator.md`. The doc exists, but the audit found no
  docs-build or link-check coverage for it.
- [ ] Add FSV as an optional dependency in `pyproject.toml` with install
  instructions. The extra exists, but the audit found no install smoke test
  for `[fedstylevalidator]`.
- [ ] Define FSV version pinning and compatibility policy. The policy doc
  exists, but the audit found no check that the documented compatibility range
  matches `pyproject.toml`.

### 41) Editor, integrations, and content management

**Phase 1 — Enterprise content integrations**

The verified Microsoft 365 WOPI host integration was moved to
`docs/latest_features.md` on 2026-03-12.

**Phase 2 — Editor hardening**

- [ ] Add offline editing support. The offline storage and sync code is
  present, but the audit found no automated offline-mode or reconnect tests for
  the TipTap editor flow.
The verified format-fidelity expansion (RTF, ODT, EPUB, LaTeX, and Confluence
wiki markup) was moved to `docs/latest_features.md` on 2026-03-12.

**Phase 3 — Enterprise search and analytics**

The verified external-search stub and analytics dashboard/export endpoints were
moved to `docs/latest_features.md` on 2026-03-12.

### 42) Configuration and extensibility

- [ ] Add theme and white-label support. Backend branding color fields are
  covered by `tests/test_item42_theming.py`, but the audit found no automated
  frontend coverage for `useTheme.ts`, Sidebar CSS variable application, or the
  branding color-picker UI.

### 45) Role-based dashboard UX improvements

Dashboards exist for User, Manager, and Admin roles with proper RBAC enforcement
and per-widget visibility customization. The following items improve discoverability
and role-appropriate navigation.

- [ ] Add a **settings cog icon** to each dashboard header (User, Manager,
  Admin). The UI change is present, but the audit found no automated frontend
  test covering the button render across dashboard variants.
- [ ] Gate dashboard links in the sidebar by role. The code is present, but
  the audit found no automated sidebar test covering admin, manager, and
  standard-user navigation states.
- [ ] Persist widget visibility preferences to SQLite. Backend persistence and
  `/dashboard/visibility` are covered by `tests/test_item45_visibility.py`, but
  the audit found no automated frontend coverage proving the dashboards load and
  save via the API instead of localStorage.

### 46) Frontend localization readiness

Backend i18n infrastructure is complete (`i18n.py`, 70 keys, 4 locales, REST
endpoints). Frontend locale JSON files exist in `public/locales/`. Next.js i18n
routing is configured. However, **zero frontend components use the i18n system** —
all UI strings are hardcoded in English.

**Phase 1 — Hook and switcher**

- [ ] Created `frontend/lib/useTranslation.ts` hook. The hook exists, but the
  audit found no automated frontend test for nested key lookup, cache behavior,
  or locale switching from the hook surface.
- [ ] Created `frontend/components/LocaleSwitcher.tsx` dropdown with 4 locales.
  The component exists, but the audit found no automated component test for
  locale switching behavior.
The verified backend locale-preference endpoints were moved to
`docs/latest_features.md` on 2026-03-12.

**Phase 2 — String extraction and migration**

- [ ] Extract hardcoded UI strings from `login.tsx`, `projects/index.tsx`, and
  `dashboard/user.tsx`. The locale files were updated, but the audit found no
  automated frontend assertions that these pages now render through the i18n
  path.
- [ ] Replace hardcoded strings with `t("key")` calls in `login.tsx`,
  `projects/index.tsx`, and `dashboard/user.tsx`. Add page-level rendering
  tests that fail if hardcoded English strings return.
- [ ] `LocaleSwitcher` added to sidebar footer. The code is present, but there
  is no automated sidebar test covering the footer render and interaction.

**Phase 3 — Full coverage**

- [ ] Migrate remaining pages and components to use `useTranslation`. The code
  changes are present, but the audit found no automated frontend coverage for
  `search.tsx`, `configuration/index.tsx`, and `profile.tsx` under alternate
  locales.
- [ ] Added `frontend/scripts/check-hardcoded-strings.mjs` lint script
  (`npm run lint:i18n`). The script exists, but the audit found no automated
  proof that it scans the intended pages or fails on a violating fixture.
- [ ] Branding/terminology overrides now applied on top of locale translations
  via `GET /i18n/terminology/{locale}?org_id=`. Backend merge behavior is
  covered by `tests/test_item46_terminology_merge.py`, but the audit found no
  automated frontend coverage for the `useTranslation({ orgId })` path.

### 47) In-app support and documentation

A "Support" link exists in the sidebar and the footer shows configurable
Support/Docs/Security/Privacy links via the branding system. However, the actual
help and documentation pages are stubs.

- [ ] Replaced `/docs/` placeholder with real in-app help. `GET /help` is
  covered by `tests/test_help_endpoint.py`, but the audit found no automated
  coverage for the promised five-tab layout.
- [ ] Flesh out `/help` content. The page content exists, but the audit found
  no automated checks for the key-concepts, FAQ, keyboard-shortcut, and API
  reference sections.
- [ ] Sidebar "Support" link replaced with collapsible "Help & Support"
  section. The UI is present, but the audit found no automated sidebar test for
  the new section and links.
- [ ] Added `HelpTooltip` component with popover. Utility escaping is covered
  by `tests/test_contextual_help.py`, but the audit found no automated frontend
  component coverage for popover rendering where the tooltips are used.
- [ ] Wire `brandingSupportUrl` and `brandingDocsUrl`. The store plumbing is
  present, but the audit found no automated sidebar test for branding-based link
  overrides.

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

- [ ] Audit `doc_validation.py`, `document_checker.py`, and
  `tiptapFederalStyleLint.ts` for checks that duplicate FSV functionality
  (style rules, acronym validation, heading structure, plain language scoring).
  Track removal behind item 34 FSV integration milestones.
- [ ] Consolidated three separate validation endpoints into
  `POST /documents/validate`. The code is present, but the audit found no
  dedicated automated coverage for the endpoint contract or the
  `checker.tsx` single-call behavior.

**Tool configurability**

- [ ] Add per-check granularity for FSV rules in the admin Configuration →
  Tools page. The settings endpoints and UI exist, but the audit found no
  targeted test for category persistence or checker behavior under different
  settings.
- [ ] Tools index page now shows Active/Disabled/Not-installed status badges,
  community labels, dimmed disabled cards, admin-only Configure links, and
  Enable/Disable toggles for built-in plugins. The UI is present, but the audit
  found no automated frontend coverage for these states.

### 49) Frontend stability — React hook violations and stale crashes

Pages crash in production with "Rendered more hooks than during the previous
render" or "Rendered fewer hooks than expected". The root cause is React's Rules
of Hooks being violated: hooks must be called in the **same order on every
render** and **never after a conditional return**. Tests miss this because Jest +
Testing Library hydrate synchronously and never hit the loading/null states that
trigger early returns. The "stale" message users see is React or Next.js
detecting that the previous render's hook count differs from the current one.

**Regression coverage still required**

- [ ] `pages/projects/[id]/index.tsx`: The `feedbackShowMyOnly` hook-order fix
  is in place, but the audit found no automated loading-to-loaded regression
  test covering this render path.

- [ ] **`router.isReady` guard added** to the affected dynamic pages. The code
  is in place, but the audit found no automated regression test across those
  route-hydration paths.

- [ ] **Stale closures fixed** in `pages/projects/[id]/index.tsx`. The cleanup
  and dependency-array changes are present, but the audit found no delayed
  response or unmount regression test for the stale-update path.

- [ ] **React Error Boundary added**. `PageErrorBoundary` exists in
  `pages/_app.tsx`, but the audit found no automated frontend test covering the
  fallback UI and reset-on-route-change behavior.

- [ ] **`useApprovals` `any` type removed**. `RawApproval` and `mapApproval`
  are in place, but the audit found no targeted hook test or frontend typecheck
  gate confirming the mapped-state contract in CI.

**Still open**

- [ ] **Hook ordering in `useProject`, `useApprovals`, `usePhases`** — hooks receive
  `undefined` during router hydration but the queries are `enabled: !!id` so no
  fetch fires. The ordering is stable because no hooks are called conditionally.
  No crash observed; keep under monitoring.

- [ ] **Frontend tests do not cover loading → loaded state transitions** — add
  `msw` (Mock Service Worker) delayed-response tests to catch future hook-ordering
  violations before they reach production.
