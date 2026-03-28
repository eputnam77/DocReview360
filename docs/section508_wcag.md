# Section 508 and WCAG 2.1 AA Compliance Guide

## Overview

DocReview360 is designed for federal government use and targets:

- **Section 508** — Rehabilitation Act (36 CFR Part 1194, revised 2017)
- **WCAG 2.1 Level AA** — Web Content Accessibility Guidelines

This guide documents compliance status, how to run automated scans, and known gaps.

---

## Conformance Scope

In-scope routes and user journeys mapped to WCAG 2.1 AA:

| Route | Key User Journey | Priority |
|-------|-----------------|----------|
| `/login` | Authenticate with username/password | Critical |
| `/signup` | Create new account | Critical |
| `/projects` | View and navigate project list | Critical |
| `/projects/[id]` | Review workflow, inline comments, track changes | Critical |
| `/approvals` | Approve/reject documents | Critical |
| `/editors/tiptap` | Rich-text editing | High |
| `/configuration/*` | Admin configuration of workflows, plugins | High |
| `/tools/*` | Document quality, converter, analysis tools | High |
| `/profile` | Update personal settings | Medium |
| `/search` | Full-text search | Medium |
| `/help` | Keyboard shortcut reference | Medium |

**Pass criteria per route (WCAG 2.1 AA):**
- Zero axe-core violations at rule level `critical` or `serious`.
- All interactive controls operable by keyboard alone (Tab/Enter/Space/Esc/Arrows).
- All form inputs have programmatically associated labels.
- Page has exactly one `<h1>`; heading hierarchy is logical.
- Color is not the only means of conveying information.
- Text contrast ≥ 4.5:1 (normal text) or 3:1 (large text / UI components).

---

## AT Test Matrix

Browser + AT combinations required for release signoff:

| Assistive Technology | Browser | Platform | Coverage |
|---------------------|---------|----------|----------|
| NVDA (latest) | Chrome (latest) | Windows 11 | Login, projects list, review flow, approvals |
| JAWS (2023+) | Edge (latest) | Windows 11 | Login, rich-text editor, configuration |
| VoiceOver | Safari (latest) | macOS Ventura+ | Login, projects list, help page |
| VoiceOver | Safari (iOS 16+) | iPhone/iPad | Login, projects list (responsive) |
| Keyboard-only | Chrome | Any | All critical routes — no AT required |
| 400% zoom | Chrome | Windows | Login, projects, editor — no horizontal scroll |
| 320 px viewport | Chrome DevTools | — | All pages — single-column reflow, no overlap |

---

## Front-End Conformance Status

> Status key: **Implemented** = code change merged; **Tested** = covered by automated tests; **Pending** = not yet done.

| Feature | Status | Evidence |
|---------|--------|----------|
| Skip-to-main-content link | Implemented, Tested | `_app.tsx`; `__tests__/a11y_skip_link.test.ts` |
| Tabs keyboard navigation (ArrowLeft/Right/Home/End) | Implemented, Tested | `components/ui/tabs.tsx`; `__tests__/a11y_tabs.test.ts` |
| Tab panel `aria-labelledby` and `tabIndex=0` | Implemented, Tested | `components/ui/tabs.tsx`; `__tests__/a11y_tabs.test.ts` |
| `?` shortcut navigates to Keyboard Shortcuts tab | Implemented, Tested | `pages/help.tsx`; `__tests__/a11y_help_shortcut.test.ts` |
| Toolbar axe-core scan | Implemented, Tested | `__tests__/accessibility.test.tsx` |
| Page-level axe coverage for public pages (signup, terms, privacy) | Implemented, Tested | `__tests__/a11y_public_pages.test.tsx` |
| `<h1>` on login page (sr-only, above CardTitle h3) | Implemented, Tested | `pages/login.tsx`; `__tests__/a11y_landmarks_forms.test.ts` |
| `<h1>` on search page | Implemented, Tested | `pages/search.tsx`; `__tests__/a11y_landmarks_forms.test.ts` |
| Search form `role="search"` landmark | Implemented, Tested | `pages/search.tsx`; `__tests__/a11y_landmarks_forms.test.ts` |
| `aria-live="assertive"` error region on login form | Implemented, Tested | `pages/login.tsx`; `__tests__/a11y_landmarks_forms.test.ts` |
| Login inputs: `aria-describedby` + `aria-invalid` on error | Implemented, Tested | `pages/login.tsx`; `__tests__/a11y_landmarks_forms.test.ts` |
| Profile form: all Label/input pairs have `htmlFor`/`id` | Implemented, Tested | `pages/profile.tsx`; `__tests__/a11y_landmarks_forms.test.ts` |
| Plugin marketplace toggle buttons: `aria-pressed` + `aria-label` | Implemented, Tested | `pages/configuration/plugin-marketplace.tsx`; `__tests__/a11y_landmarks_forms.test.ts` |
| Table component: `<caption>`, `<thead>`, `<th scope="col">` | Implemented, Tested | `components/ui/table.tsx`; `__tests__/a11y_table_controls.test.ts` |
| Dialog/modal focus trap via Radix UI | Implemented, Tested | `components/ui/dialog.tsx`, `modal.tsx`; `__tests__/a11y_table_controls.test.ts` |
| `prefers-reduced-motion` CSS (WCAG 2.3.3) | Implemented, Tested | `styles/globals.css`; `__tests__/a11y_visual.test.ts` |
| CSS design tokens: foreground/background in light + dark | Implemented, Tested | `styles/globals.css`; `__tests__/a11y_visual.test.ts` |
| Button focus-visible ring (WCAG 2.4.7) | Implemented, Tested | `components/ui/button.tsx`; `__tests__/a11y_visual.test.ts` |
| Page-level axe coverage for critical flows (login, project creation, review, approvals, editor) | Pending | — |
| Contrast audit — manual measurement of token pairs (4.5:1 AA) | Pending — needs manual review | — |
| Zoom/reflow at 320 px / 400% — manual browser check | Pending — needs manual review | — |
| AT manual test script (NVDA, VoiceOver) per matrix above | Pending | — |

---

## Automated Accessibility Scanning

### API Endpoint

`POST /tools/accessibility-scan` (requires authentication)

```json
{
  "document_id": "doc-abc123",
  "content": "<html>...</html>"
}
```

Returns:
```json
{
  "document_id": "doc-abc123",
  "checked_at": "2026-03-11T00:00:00Z",
  "wcag_level": "AA",
  "score": 85,
  "violations": [
    {
      "criterion": "WCAG 1.1.1",
      "severity": "error",
      "description": "One or more images are missing alt text",
      "element": "<img>"
    }
  ],
  "passes": [
    "WCAG 2.4.4 — Links have descriptive text",
    "WCAG 4.1.2 — Buttons have accessible names"
  ]
}
```

### Score Interpretation

| Score | Status |
|-------|--------|
| 90–100 | Excellent — minor warnings only |
| 70–89 | Acceptable — address warnings |
| 50–69 | Needs work — errors present |
| < 50 | Critical — major barriers exist |

---

## WCAG 2.1 AA Criteria Coverage

### Automatically Checked (via `/tools/accessibility-scan`)

| Criterion | Description | Checked |
|-----------|-------------|---------|
| 1.1.1 Non-text Content | Images have alt text | ✅ |
| 1.3.1 Info and Relationships | Heading hierarchy is sequential | ✅ |
| 1.3.5 Identify Input Purpose | Form inputs have labels | ✅ |
| 2.4.4 Link Purpose | Links have descriptive text | ✅ |
| 3.1.1 Language of Page | `<html lang="...">` is set | ✅ |
| 4.1.2 Name, Role, Value | Buttons have accessible names | ✅ |

### Requires Manual Testing

| Criterion | Description | Status |
|-----------|-------------|--------|
| 1.2.x Captions and Audio Description | Video/audio content captions | Manual |
| 1.4.1 Use of Color | Color is not the only conveyor of information | Manual |
| 1.4.3 Contrast Minimum | Text contrast ≥ 4.5:1 (AA) | Manual / design review |
| 1.4.4 Resize Text | Text resizes to 200% without content loss | Manual |
| 1.4.10 Reflow | Content reflows at 320px without horizontal scrolling | Manual |
| 2.1.1 Keyboard | All functionality is keyboard accessible | Manual |
| 2.4.7 Focus Visible | Keyboard focus indicator is visible | Manual |
| 2.5.3 Label in Name | Labels match or contain visible text | Manual |
| 3.2.4 Consistent Identification | Components named consistently across pages | Manual |
| 3.3.1 Error Identification | Errors are identified in text | Manual |

---

## Section 508 Mapping

| Section 508 Provision | Description | Coverage |
|----------------------|-------------|----------|
| E205.3 (WCAG 2.0 Level A/AA) | Applies WCAG 2.0 to software | WCAG 2.1 is a superset — covered |
| E207.2 (Software) | Screen reader and AT compatibility | TipTap editor uses ARIA roles |
| E401.1 (Applicable Standards) | Standards referenced by ICT | WCAG 2.1 AA |

---

## Keyboard Navigation Notes

- All primary navigation links are keyboard accessible (tab-indexed in order).
- Modal dialogs trap focus while open; `Esc` closes them.
- Data tables include `<th scope="col">` headers for screen readers.
- Form inputs use `<label for="...">` associations throughout.
- **Implemented:** Skip-to-main-content link is present in the app shell (`_app.tsx`), visible on keyboard focus, and moves focus to the `<main>` container.
- **Implemented:** Custom Tabs component (`components/ui/tabs.tsx`) supports ArrowLeft/ArrowRight/Home/End keyboard navigation per ARIA tablist pattern; inactive tabs use `tabIndex=-1`; tab panels have `aria-labelledby` and `tabIndex=0`.
- **Implemented:** `?` key on the Help page navigates to the Keyboard Shortcuts tab.
- **Implemented:** All form inputs in login and profile pages have programmatically associated `<label>` elements via `htmlFor`/`id` pairs.
- **Implemented:** Login page announces authentication errors via an `aria-live="assertive"` region; inputs gain `aria-invalid` and `aria-describedby` on failure.
- **Implemented:** Plugin marketplace toggle buttons expose `aria-pressed` (current state) and a descriptive `aria-label` for icon-only controls.
- **Implemented:** `prefers-reduced-motion` media query in `globals.css` suppresses animations and transitions for users who have configured this OS preference.

## Screen Reader Compatibility

DocReview360 has been designed for compatibility with:
- JAWS (Windows)
- NVDA (Windows)
- VoiceOver (macOS / iOS)

The TipTap rich text editor uses ProseMirror's accessibility layer with `role="textbox"` and
`aria-multiline="true"`. Complex editor features (inline comments, track changes) should be
audited with AT before production deployment in a screen-reader-heavy environment.

---

## Reporting Accessibility Issues

File accessibility issues at the project issue tracker with the label `a11y`. Include:
1. URL or page/feature affected
2. AT and browser combination
3. Expected behavior
4. Actual behavior
5. Steps to reproduce

---

## Integration with CI/CD

Add accessibility scanning to your CI pipeline using the API:

```bash
# Example: scan a rendered HTML document via API
curl -s -X POST http://localhost:8000/tools/accessibility-scan \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "'"$DOC_ID"'"}' | jq '.score'
```

Fail the build if score < 70:

```bash
SCORE=$(curl -s ... | jq '.score')
[ "$SCORE" -lt 70 ] && echo "Accessibility score too low: $SCORE" && exit 1
```
