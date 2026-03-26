# Front-End Accessibility Gap Assessment and Implementation Tasks

## Executive assessment

DocReview360 has **good accessibility intent** and some solid implementation patterns (semantic `<main>`, ARIA labels, focus ring styles, and basic axe coverage), but it does **not yet demonstrate full Section 508 / WCAG 2.1 AA readiness** for the full front-end experience.

The current codebase shows a gap between:

- what the docs claim (broad compliance), and
- what is actually verified automatically and manually in UI flows.

So the practical status is: **partially accessible, not yet compliance-proven**.

---

## Evidence observed in the codebase

### What is already in place

- App shell has a semantic `<main>` region and sidebar `<nav>` usage, which is a good baseline.
- Many controls include explicit accessible names (e.g., `aria-label`) and visible focus styling.
- There is an accessibility unit test using axe-core for toolbar button rendering.
- The help page documents keyboard shortcuts; editor-level shortcuts exist (commenting, track-changes toggles).

### Material gaps to close

- Accessibility testing is narrow: only a toolbar-level axe check, not full-page or critical-flow coverage.
- Custom tabs component lacks expected keyboard interactions (Left/Right/Home/End) for tablists.
- No global “skip to main content” link to bypass persistent sidebar navigation.
- Help page lists `?` as a shortcut, but there is no corresponding keybinding implementation on that page.
- Repo docs currently claim stronger keyboard/dialog/table coverage than is evidenced by automated tests.

---

## Implementation task plan

> Goal: move from “best effort” to **auditable WCAG 2.1 AA conformance evidence** for the front end.

### Track 1 — Baseline and acceptance criteria (foundational)

1. **Define conformance scope**
   - Enumerate in-scope routes and user journeys (login, project creation, review workflow, approvals, editor, configuration).
   - Define explicit pass/fail criteria per route mapped to WCAG 2.1 AA.

2. **Create an accessibility test matrix**
   - Browser + AT combinations: NVDA/JAWS + Chrome/Edge, VoiceOver + Safari.
   - Include keyboard-only, zoom/reflow (200%/400%), and contrast checks.

3. **Add CI-grade automation**
   - Add page-level axe tests for top workflows, not just isolated components.
   - Add a manual-test checklist artifact required for release signoff.

### Track 2 — Keyboard and focus operability (highest priority)

4. **Add “Skip to main content” in app shell**
   - Add skip link before sidebar in `_app.tsx`.
   - Ensure it becomes visible on keyboard focus and moves focus to the main container.

5. **Upgrade custom Tabs keyboard behavior**
   - Implement ArrowLeft/ArrowRight (and optionally Home/End) on `TabsTrigger`/`TabsList`.
   - Keep active tab in tab order (`tabIndex=0`) and inactive tabs `-1`.

6. **Audit all custom interactive widgets for keyboard parity**
   - Validate Enter/Space activation for custom button-like containers.
   - Ensure modal/dialog/drawer focus trap + initial focus + return-focus behavior is consistent.
   - Ensure Escape closes overlays only when contextually appropriate.

7. **Fix shortcut consistency**
   - Either implement the `?` shortcut on Help page or remove/document it accurately.
   - Build a shortcut registry to avoid mismatch between docs and behavior.

### Track 3 — Screen-reader and semantic quality

8. **Landmarks and names audit**
   - Ensure every page has one clear `<h1>` and meaningful region labels where needed.
   - Validate menu/dialog/tabpanel relationships with IDs and `aria-controls`/`aria-labelledby`.

9. **Form and error announcement improvements**
   - Standardize error summaries and field-level error linking (`aria-describedby`).
   - Add `aria-live` for async success/error toasts where users need immediate feedback.

10. **Table and complex control review**
   - Verify header associations and row action menu keyboard model in approvals and config tables.

### Track 4 — Visual accessibility and robustness

11. **Contrast audit (light/dark themes)**
   - Audit token combinations and component states (default/hover/disabled/focus).
   - Remediate any sub-4.5:1 text or low-contrast focus indicators.

12. **Zoom/reflow/responsive checks**
   - Verify at 320px CSS width and 400% zoom without loss of content/function.

13. **Motion and target-size checks**
   - Add reduced-motion handling where animated UI could affect users.
   - Validate interactive hit-area sizing for key controls.

### Track 5 — Governance and documentation integrity

14. **Align compliance documentation with evidence**
   - Update `docs/section508_wcag.md` to clearly separate “implemented”, “tested”, and “pending” status.
   - Attach evidence links to test runs and manual reports.

15. **Release gate**
   - Add an accessibility gate in release checklist requiring:
     - passing automated accessibility checks,
     - completed manual AT script for critical flows,
     - no unresolved critical WCAG blockers.

---

## Keyboard shortcuts: do we need them to get around the UI?

**Strict compliance answer:**
- You do **not** need global keyboard shortcuts to satisfy WCAG keyboard criteria.
- You **do** need all functions to be operable by keyboard alone (Tab/Shift+Tab/Enter/Space, with proper focus visibility and order).

**Productivity answer:**
- Keyboard shortcuts are still recommended for power users (especially in editor-heavy workflows).
- If implemented, they must be discoverable, avoid conflicts, and support remapping/disable patterns where practical.

---

## Suggested rollout sequence

1. Track 1 (scope + test matrix + CI hooks)
2. Track 2 (skip link + tabs keyboard model + shortcuts consistency)
3. Track 3 (screen reader/error semantics)
4. Track 4 (contrast/reflow/motion)
5. Track 5 (docs + release gate)

This sequence gives the fastest risk reduction and produces defensible compliance evidence early.
