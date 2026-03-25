# Federal Style Validator Integration — UX and Branding Tasks

> Federal Style Validator (FSV / FedStyleValidator) is an add-in for DocReview360.
> FSV also runs as a standalone web application.
> This document tracks work needed in DocReview360 to ensure the two products share
> consistent branding, color palette, and user experience when FSV is embedded or linked.
>
> Companion checklist in FSV repo: `RELEASE_CHECKLIST.md § 5. Frontend UX, Branding, and Message Clarity`
> Last reviewed: 2026-03-25.

---

## 1. Branding and Visual Consistency

- [ ] `DR-FSV-1` **Consume shared FSV brand tokens.** FSV will publish a `brand-tokens.json`
  (tracked in `RELEASE_CHECKLIST.md UX-12`) defining canonical color values for primary
  action, severity indicators, and background surfaces. Once that file exists, update
  `frontend/state/branding.ts` so the FSV-specific color slot (`brandingPrimaryColor` when
  applied to the FSV add-in surface) reads from those tokens rather than hardcoding a value.
  This prevents color drift as FSV's design evolves.

- [ ] `DR-FSV-2` **Align the FSV checker page with DocReview360's light theme.**
  `frontend/pages/tools/checker.tsx` proxies results from FSV. FSV currently forces a
  dark background (`#0f172a`) inside its results iframe. Once FSV adds light-mode support
  (FSV `UX-10`), update the checker page to pass a `theme=light` query parameter or header
  so the embedded results render on a white/light-gray surface consistent with the rest of
  DocReview360 rather than appearing as a dark block inside a light page.

- [ ] `DR-FSV-3` **Match the FSV results severity colors to DocReview360's system colors.**
  DocReview360 uses `red-600` for errors, `amber-600` for warnings, and `indigo-600`/`blue-600`
  for info. FSV uses `#ef4444`, `#f59e0b`, and `#0ea5e9`. These are close but not identical,
  so the severity pills in the FSV checker page look slightly different from DocReview360's
  own alert styles. Remap the severity border/badge colors in the checker page to use
  DocReview360's Tailwind color tokens (`text-red-600`, `text-amber-600`, `text-blue-600`)
  so severity indicators are visually consistent across the full product.

---

## 2. FSV Checker Page UX (`frontend/pages/tools/checker.tsx`)

- [ ] `DR-FSV-4` **Show a clear zero-issues success state.** When FSV returns 0 findings the
  checker page currently renders nothing (empty results area). Render a success banner:
  green `CheckCircle` icon, "No style issues found" heading, and a one-line explanation of
  which check categories ran. This matches the success-state task in FSV (`UX-3`) and gives
  users confidence the run actually completed.

- [ ] `DR-FSV-5` **Surface actionable fix instructions in DocReview360's results display.**
  The checker page renders FSV findings as a plain list. Each finding should display:
  (1) severity badge, (2) message text, (3) the applicable style authority (AP Style,
  FAA Order 1320.46D, etc.), and (4) an inline "How to fix" summary. This aligns with the
  message-quality work in FSV (`UX-6`, `UX-7`) and avoids users needing to look up the
  rule elsewhere.

- [ ] `DR-FSV-6` **Add per-category collapsible sections to the results display.**
  When a document has many issues, the flat list in the checker page becomes unnavigable.
  Group findings by check category (Heading, Format, Accessibility, etc.) with collapsible
  `<details>` or Accordion components and show a count badge per category. This mirrors
  the grouping work planned for FSV's own UI (`UX-4`) and is consistent with how
  DocReview360 presents multi-item workflow results elsewhere.

- [ ] `DR-FSV-7` **Add a loading skeleton while FSV processes the document.**
  The checker page shows no feedback between upload and result display. Add a loading
  skeleton (3–4 gray placeholder rows) while `POST /tools/checker` is in flight.
  Use DocReview360's existing Skeleton component from `components/ui/` for consistency.

- [ ] `DR-FSV-8` **Show FSV service status prominently when unavailable.**
  When `GET /fsv/status` returns an error or times out the checker page shows a generic
  error. Replace this with a clear, user-friendly banner: "Federal Style Validator service
  is currently unavailable. Contact your administrator or try again later." Include the
  admin settings link (`/admin/settings/fsv-url`) for users with admin role so they can
  reconfigure without searching.

---

## 3. Editor Integration (On-Save Validation Pill)

- [ ] `DR-FSV-9` **Match the quality score pill colors to DocReview360's semantic colors.**
  The TipTap editor toolbar shows a colored pill from the cached `DocumentQualityScore`.
  The pill color thresholds (green/yellow/red) are currently independent of the severity
  colors used in the checker page and FSV. Standardize thresholds and colors:
  score ≥ 0.8 → `green-600` ("Good"), 0.5–0.79 → `amber-600` ("Needs attention"),
  < 0.5 → `red-600` ("Issues found"). Use the same Tailwind tokens as the checker page.

- [ ] `DR-FSV-10` **Make the quality score pill a link to the checker page.**
  Clicking the pill in the editor toolbar should navigate to `tools/checker` with the
  current document pre-selected so users can see the full findings without re-uploading.
  This requires passing `document_id` as a query parameter; update the checker page to
  accept and auto-load it.

---

## 4. Plugin Marketplace and Admin Settings

- [ ] `DR-FSV-11` **Use consistent terminology: "Federal Style Validator" everywhere.**
  The plugin marketplace (`frontend/pages/configuration/plugin-marketplace.tsx`) and
  the tools index page (`frontend/pages/tools/index.tsx`) use "FedStyleValidator" and
  "Federal Style Validator" interchangeably. Standardize to "Federal Style Validator"
  (the full product name) in all user-facing strings, and "FSV" as the short form in
  technical/admin contexts only.

- [ ] `DR-FSV-12` **Add a "Test connection" button to the FSV URL admin settings page.**
  `frontend/pages/admin/settings/` (FSV URL config) has a text field for the FSV endpoint
  but no way to verify it is reachable without re-uploading a document. Add a "Test
  connection" button that calls `GET /fsv/status` and shows a pass/fail result inline.
  This reduces misconfiguration support burden.
