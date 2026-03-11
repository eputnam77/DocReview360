# Section 508 and WCAG 2.1 AA Compliance Guide

## Overview

DocReview360 is designed for federal government use and targets:

- **Section 508** — Rehabilitation Act (36 CFR Part 1194, revised 2017)
- **WCAG 2.1 Level AA** — Web Content Accessibility Guidelines

This guide documents compliance status, how to run automated scans, and known gaps.

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
