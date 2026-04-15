# Frontend Stability Findings

Date: 2026-04-15
Confidence: 0.95

## Executive summary

The frontend is a React app running on Next.js, not a Vite app.

The local evidence is clear:

- [`frontend/package.json`](frontend/package.json) uses `next dev`, `next build`, and `next start`.
- [`frontend/next.config.js`](frontend/next.config.js) configures a Next.js app.
- [`frontend/pages/_app.tsx`](frontend/pages/_app.tsx) provides the shared app shell for the Pages Router.

The stronger finding is not framework choice. It is frontend brittleness caused by complexity. The highest-risk files are currently:

- `frontend/pages/projects/[id]/index.tsx`: about 3360 lines
- `frontend/components/TiptapEditorFull.tsx`: about 1730 lines

That size, combined with TipTap, Yjs, React Query, dialogs, browser APIs, and local storage, is a credible explanation for the crash-fix-crash loop even when build and unit tests pass.

## What I verified locally

On 2026-04-15 I ran these checks in `frontend/`:

- `npm run build`
- `npm test`

Results:

- Production build passed.
- Frontend test suite passed.
- Vitest reported `62` passing test files and `654` passing tests.

This means the current problem is not "the app cannot build" or "the existing unit suite is red." It means the current checks are not strong enough to catch the runtime failures you are seeing in the browser.

## Findings

### 1. This is a Next.js Pages Router app

The repo structure matches a Next.js Pages Router application:

- `frontend/pages/` contains route files
- `frontend/pages/_app.tsx` wraps the shared shell
- `frontend/next.config.js` configures framework behavior

That aligns with the Next.js Pages Router model, where files in `pages/` map to routes and `_app` controls shared page initialization and layout behavior.

### 2. The main problem is complexity, not framework selection

The current frontend has multiple risk multipliers in the same runtime path:

- Large route components
- Large editor component
- Rich editor lifecycle
- Collaborative document state
- Query cache state
- Local storage usage
- Browser-only APIs such as `window` and `document`
- Modal/dialog behavior

Any one of these is manageable. Together, they increase the odds of:

- client-only code leaking into SSR paths
- hydration mismatches
- editor initialization order bugs
- stale state interactions across dialogs, route changes, and autosave
- runtime-only failures that unit tests do not exercise

### 3. Existing browser automation already exists, but the gap is still real

The repo already includes Playwright-based E2E infrastructure through the Python test layer:

- [`pyproject.toml`](pyproject.toml) includes `pytest-playwright` and `playwright`
- [`docs/testing_and_quality.md`](docs/testing_and_quality.md) documents `python scripts/run_e2e.py`
- [`tests/e2e/test_project_profile_e2e.py`](tests/e2e/test_project_profile_e2e.py) shows active browser-driven tests

So the recommendation is not "add Playwright from scratch." The recommendation is:

- extend the existing E2E smoke gate
- make browser console errors and page runtime errors fail the test immediately
- focus the smoke set on the crash-prone frontend routes

### 4. There are still runtime-quality warning signals

The passing test run still emitted React warnings during frontend tests, including warnings in the `ProjectDetailsPage` and `VersionDrawer` path. Those warnings are not the root cause by themselves, but they are a sign that some component contracts are loose enough to allow browser-only regressions to slip through.

## Recommendation

Do not switch from Next.js to Vite first.

A Vite migration would be a significant rewrite and would not automatically fix:

- SSR/client boundary mistakes
- hydration issues
- editor lifecycle bugs
- local storage timing bugs
- oversized components that are hard to reason about

The better path is:

1. Strengthen browser crash detection.
2. Stabilize the crash-prone flows.
3. Break up the largest route and editor components.
4. Re-evaluate framework fit only after the frontend is observable and testable.

## Implementation tasks

### Phase 1. Stop silent browser crashes

Task 1. Add a frontend crash gate to the existing Playwright smoke flow.

Status: done on 2026-04-15.

Implemented in:

- `tests/e2e/runtime_guard.py`
- `tests/e2e/conftest.py`
- `tests/test_e2e_runtime_guard.py`

- Add shared Playwright helpers that fail on:
  - uncaught page exceptions
  - console errors
  - failed network requests for required page data
  - unhandled promise rejections surfaced in the page
- Wire those helpers into the existing `e2e_smoke` path instead of creating a second browser test harness.
- Record the first failing route, error message, and stack in test output.

Verification:

- `python -m pytest tests/test_e2e_runtime_guard.py tests/test_e2e_run_determinism.py -q`
- `python -m pytest tests/e2e --collect-only -q`

Verification note:

- Full `e2e_smoke` browser execution is currently blocked by an existing backend `/e2e/seed` 500 error caused by duplicate document-type seeding, which is separate from the frontend crash-gate change.

Task 2. Expand smoke coverage for the routes most likely to crash.

Status: done on 2026-04-15.

Implemented across:

- `tests/e2e/test_login_e2e.py`
- `tests/e2e/test_project_profile_e2e.py`
- `tests/e2e/test_workflow_e2e.py`

- Add smoke coverage for:
  - `/projects`
  - `/projects/[id]`
  - `/projects/[id]/edit`
  - `/projects/[id]/review`
  - `/editors/tiptap`
  - `/dashboard`
  - `/configuration/document-types`
- Keep assertions minimal at first: page loads, no uncaught errors, key shell elements render, and critical API calls complete.

Verification:

- `python -m pytest tests/e2e --collect-only -q`

Verification note:

- Full `e2e_smoke` browser execution remains blocked by the existing backend `/e2e/seed` 500 error noted above. Route coverage has been implemented, but end-to-end execution cannot be completed until that backend seeding failure is fixed.

Task 3. Fail CI on frontend browser crashes.

Status: done on 2026-04-15.

Satisfied by:

- `.github/workflows/ci.yml` existing `e2e-smoke` job
- `tests/e2e/conftest.py` runtime crash gate added in Task 1
- `scripts/run_e2e.py` existing `E2E_TEST_MARK=e2e_smoke` runner path

- Add a required smoke gate that runs the Playwright smoke subset with crash detection enabled.
- Keep full E2E coverage as a broader gate, but make the smoke gate the fast blocker for frontend regressions.

Verification:

- `.github/workflows/ci.yml` already runs `E2E_TEST_MARK=e2e_smoke`
- frontend runtime crash detection is now attached to `e2e_smoke` in `tests/e2e/conftest.py`

### Phase 2. Harden browser-only boundaries

Task 4. Audit browser-only usage in crash-prone components.

Status: done on 2026-04-15.

Implemented in:

- `frontend/lib/browser.ts`
- `frontend/pages/projects/[id]/index.tsx`
- `frontend/components/TiptapEditorFull.tsx`
- `frontend/__tests__/browser.test.ts`
- `frontend/__tests__/ProjectDetailsPage.test.tsx`
- `frontend/__tests__/ProjectDetailsPage.test.jsx`
- `frontend/__tests__/projectDocumentPreview.test.tsx`

- Review `window`, `document`, `localStorage`, `sessionStorage`, `matchMedia`, and editor DOM assumptions in:
  - `frontend/pages/projects/[id]/index.tsx`
  - `frontend/components/TiptapEditorFull.tsx`
  - supporting editor and dialog components
- Move access behind guarded client-only code paths where needed.

What changed:

- Added shared browser-safety helpers for storage access, prompts, reloads, URL resolution, redirects, and blob downloads.
- Replaced direct `localStorage`, `window.prompt`, `window.location.reload`, `window.location.assign`, and `document.createElement("a")` usage in the project detail page with guarded helper calls.
- Replaced direct draft `localStorage` access in `TiptapEditorFull` with guarded helper calls.
- Added an explicit browser check before the template-picker outside-click listener is attached in `TiptapEditorFull`.

Verification:

- `npm test -- __tests__/browser.test.ts __tests__/ProjectDetailsPage.test.tsx __tests__/ProjectDetailsPage.test.jsx __tests__/projectDocumentPreview.test.tsx`
- `npm run build`

Task 5. Put editor-heavy modules behind explicit client-only loading boundaries.

- For browser-only editor modules, use Next.js dynamic import with SSR disabled where appropriate.
- Keep server-safe shells small and deterministic.
- Separate page shell rendering from editor bootstrapping.

Task 6. Tighten dialog and component contracts.

- Fix React warnings that indicate props are leaking to DOM nodes or component wrappers are mismatched.
- Start with the `ProjectDetailsPage` and `VersionDrawer` path because it already emits warnings in tests.

### Phase 3. Reduce complexity in the highest-risk files

Task 7. Split `frontend/pages/projects/[id]/index.tsx` by responsibility.

Recommended slices:

- page data loading and query orchestration
- project summary header
- approvals section
- review activity and comments
- document preview panels
- signature flows
- version history and related dialogs
- utility hooks and derived view state

Task 8. Split `frontend/components/TiptapEditorFull.tsx` by responsibility.

Recommended slices:

- editor shell and mounting
- extension registration
- collaboration wiring
- autosave and offline draft handling
- template loading
- review markers, comments, and track changes
- submit and publish actions
- toolbar and command UI

Task 9. Convert crash-prone behavior into small hooks and adapters.

- Prefer focused hooks for local storage, autosave timers, route guards, and editor bootstrapping.
- Keep UI components mostly declarative.

## Test plan

### Browser smoke tests

Add or expand smoke tests that verify:

- routes render without uncaught exceptions
- no console errors occur during initial load
- critical user actions do not trigger page crashes
- editor page mounts cleanly before editing starts
- project details page loads dialogs and preview panels without runtime errors

Suggested smoke cases:

1. Login and open `/projects`.
2. Open a known project details page and verify the main content area renders.
3. Toggle version history, approvals, and preview panels without console or page errors.
4. Open `/editors/tiptap?id=<doc-id>` and verify editor mount, typing, and save/submit path.
5. Open `/configuration/document-types` and verify the table renders and row expansion does not crash.

### Unit and integration tests

Add focused tests for:

- SSR-safe helpers that read browser globals only when available
- dynamic import wrappers for editor-only modules
- dialog wrapper components so unsupported props do not leak to DOM nodes
- hooks for local storage and autosave timers
- query-loading states for project detail sub-sections after extraction

### Regression tests for real crashes

For each real crash:

1. Capture the route, action, and exact browser error.
2. Add a minimal reproduction test at the lowest useful level.
3. Keep one browser-level regression test if the issue was only visible in a real page flow.

### Release gate

Before merge for frontend-heavy changes, run:

- `npm test` in `frontend/`
- `npm run build` in `frontend/`
- `E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_smoke python scripts/run_e2e.py`

## Definition of done

The frontend stabilization work is in a good state when all of the following are true:

- the frontend smoke gate fails on browser runtime errors
- the main crash-prone routes are covered by browser smoke tests
- the project details route and TipTap editor are split into smaller modules
- browser-only code paths are explicit and SSR-safe
- current React warnings in the high-risk route paths are removed
- a real crash can be reproduced, fixed, and held by regression tests

## Conclusion

The current evidence does not support replacing Next.js with Vite as the first move.

It supports a different conclusion: the frontend is too brittle in a few high-complexity areas, and the missing control is browser-level crash detection plus targeted decomposition. The best next step is to strengthen the existing Playwright smoke gate and then split the crash-prone page and editor code into smaller units.

## Sources

Local repository evidence:

- [`frontend/package.json`](frontend/package.json)
- [`frontend/next.config.js`](frontend/next.config.js)
- [`frontend/pages/_app.tsx`](frontend/pages/_app.tsx)
- [`frontend/pages/projects/[id]/index.tsx`](frontend/pages/projects/[id]/index.tsx)
- [`frontend/components/TiptapEditorFull.tsx`](frontend/components/TiptapEditorFull.tsx)
- [`pyproject.toml`](pyproject.toml)
- [`docs/testing_and_quality.md`](docs/testing_and_quality.md)
- [`tests/e2e/test_project_profile_e2e.py`](tests/e2e/test_project_profile_e2e.py)

Official references:

- Next.js Pages Router docs: https://nextjs.org/docs/pages
- Next.js Pages and Layouts docs: https://nextjs.org/docs/pages/building-your-application/routing/pages-and-layouts
- Next.js lazy loading docs: https://nextjs.org/docs/pages/building-your-application/optimizing/lazy-loading
- Playwright intro: https://playwright.dev/docs/intro
- Tiptap overview: https://tiptap.dev/docs/editor/getting-started/overview
- Yjs introduction: https://docs.yjs.dev/
