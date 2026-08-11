# Release and Feature History

This file previously held a long-running feature checklist and became stale over time.

Use these sources instead:

- [`CHANGELOG.md`](changelog.md) for released changes by version.
- `RELEASE_CHECKLIST.md` (repository root) for current in-progress release tasks.

Documentation policy:

- Keep historical release details in `CHANGELOG.md`.
- Keep actionable open release work in `RELEASE_CHECKLIST.md`.
- Avoid duplicating both in this docs page.

## Tools Information Architecture (2026-03-26)

**Document Quality Checker** (`/tools/document-quality`) now consolidates all
validation-engine surfaces into a single tabbed page:

- **Federal Style Validator** is listed as the first (and currently only active)
  validation engine — it covers FAA/DoD style, plain language, acronyms,
  regulatory references, readability, and accessibility compliance.
- A second **Additional Engines** tab is reserved for future integrations
  (Grammarly, Acrolinx, open-source grammar engines) and displays a
  "Coming Soon" placeholder until a second checker is added.
- **Document Converter** (`/tools/converter`) remains a standalone page.
- `/tools/checker` now redirects to `/tools/document-quality` to avoid
  duplicate entry points.
