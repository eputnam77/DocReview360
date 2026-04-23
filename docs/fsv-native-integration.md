# FSV Native Integration — Project Tracking

**Status:** In progress  
**Started:** 2026-04-23  
**Owner:** Eric Putnam

## Problem

The Document Quality Checker page (`/tools/document-quality`) previously embedded the FSV
frontend via an `<iframe>`. This required:

1. The FSV Vite dev server running separately on port 5173
2. `NEXT_PUBLIC_FSV_FRONTEND_URL` set in `frontend/.env.local`

In production this meant customers had to run two separate applications. The iframe approach
also prevented authentication integration (FSV has no auth) and blocked customization.

## Solution

Replace the iframe with a **native DocReview360 page** that:

- Works out of the box with no external server — uses DR360's own backend API
- Automatically upgrades to full FSV results when the FSV backend
  (`FEDERAL_STYLE_VALIDATOR_URL`) is configured
- Requires only a single DR360 deployment for customers

## Architecture

```
Browser → DocReview360 frontend (Next.js)
            ↓ authenticatedFetch (JWT auth)
          DocReview360 backend (FastAPI)
            ↓ httpx proxy (when configured)
          FSV backend (Python) ← optional
```

### New backend endpoints (`tools_router.py`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/tools/document-quality` | Upload DOCX, run validation, return findings |
| `GET` | `/tools/document-quality/style-guide` | Style guide content |
| `GET` | `/tools/document-quality/rules-reference` | Rules reference content |
| `GET` | `/tools/document-quality/usage` | Usage metrics |
| `GET` | `/tools/document-quality/reports` | Recent validation reports |
| `GET` | `/tools/document-quality/results/{id:path}` | Proxy file downloads (DOCX/PDF/JSON) |

### `POST /tools/document-quality` behavior

**When `FEDERAL_STYLE_VALIDATOR_URL` is set:**
1. Proxy multipart upload to FSV `/process`
2. Fetch canonical JSON from FSV `/results/{id}.json`
3. Return merged response (full findings + summary)

**When FSV is not configured (internal path):**
1. Extract text from DOCX via `convert_document_content`
2. Run `_preflight_validate` → acronym + heading issues
3. Run `validate_style(force=True)` → style suggestions
4. Run `score_plain_language` → readability finding if score < 60
5. Return FSV-compatible findings list

### Frontend (`pages/tools/document-quality.tsx`)

Self-contained native page. All components are inline (no separate component files):

- **UploadPanel** — drag-and-drop DOCX upload + doc type selector
- **VisibilityToggles** — collapsible category enable/disable checkboxes
- **SeverityToggles** — collapsible severity filter (all/errors-only/hide-info)
- **ResultsPane** — findings grouped by category, collapsible `<details>` per group
- **ReferenceTab** — shared component for Style Guide + Rules Reference tabs (fetches markdown, renders inline)
- **MetricsTab** — usage stats + recent reports table
- **DocumentQualityPage** — main export, manages all state

All API calls use `authenticatedFetch` (JWT Bearer + CSRF). No MUI dependency. Tailwind only.

## Behavior by mode

| Feature | Internal (no FSV) | FSV backend configured |
|---------|-------------------|------------------------|
| DOCX upload + findings | Yes (preflight + style) | Yes (full FSV rules) |
| Style Guide tab | Placeholder text | Full FSV content |
| Rules Reference tab | Placeholder text | Full FSV rules catalog |
| Metrics tab | Empty stats | FSV usage metrics |
| Download DOCX/PDF | Not available | Via proxy endpoints |

## Environment variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `FEDERAL_STYLE_VALIDATOR_URL` | Backend `.env` | FSV backend base URL (e.g. `http://fsv-service:8000`) |
| ~~`NEXT_PUBLIC_FSV_FRONTEND_URL`~~ | ~~Frontend `.env.local`~~ | **No longer needed** |

`NEXT_PUBLIC_FSV_FRONTEND_URL` is no longer required. The `frontend/.env.local` file only
needs `NEXT_PUBLIC_API_BASE`.

## Files changed

| File | Change |
|------|--------|
| `src/docreview360/api/tools_router.py` | Added 6 new endpoints |
| `frontend/pages/tools/document-quality.tsx` | Full rewrite — native page replaces iframe |
| `frontend/.env.local` | Created (was missing); removed `NEXT_PUBLIC_FSV_FRONTEND_URL` |
| `CLAUDE.md` | Fixed documented FSV port: 3001 → 5173 |

## Testing checklist

- [ ] Upload a `.docx` file — findings appear in Validator tab
- [ ] Toggle category visibility — hidden categories are excluded from results
- [ ] Toggle severity filters — filtered severities disappear from results
- [ ] Style Guide tab loads (placeholder or FSV content)
- [ ] Rules Reference tab loads
- [ ] Metrics tab loads (empty or FSV data)
- [ ] With `FEDERAL_STYLE_VALIDATOR_URL` set: results show `source: fsv`
- [ ] Without FSV URL: results show `source: internal`
- [ ] Download buttons appear only when `result_id` is non-null (FSV mode)
- [ ] All tabs accessible by keyboard
- [ ] Auth required — unauthenticated requests return 401

## Known limitations

- Internal path produces fewer findings than FSV (no paragraph-length, format, or
  structure checks — those require FSV's analysis engine)
- Style issues only run when text is extractable from the DOCX
- Download buttons (DOCX/PDF) are only available in FSV mode
