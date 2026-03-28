# Release Notes — Completed Items

This file records features and fixes that are fully implemented and tested.
Items here have been verified against source code and have automated test coverage.
See `RELEASE_CHECKLIST.md` (root) and `docs/release_checklist.md` for remaining open work.

---

## Item 44 — Review cycle and project view

All six sub-items are complete as of 2026-03-28.

**Document preview panels**
- Added a read-only document preview beside the feedback table.
- Added collapsible preview panels on both the Feedback tab and the Signatures tab.
- Touch: `frontend/pages/projects/[id]/index.tsx`
  (`data-testid="feedback-preview-panel"`, `data-testid="signatures-preview-panel"`)
- Tests: `frontend/__tests__/projectDocumentPreview.test.tsx`

**Inline comment anchoring (TipTap CommentMark)**
- New TipTap Mark extension anchors comments to selected text via `data-comment-id`.
- Commands: `addComment(commentId, metadata)`, `removeComment(commentId)`.
- Keyboard shortcut: `Mod-Alt-m`.
- Utility: `extractCommentsFromDoc(doc)` walks a TipTap JSON document and returns all anchored comments.
- Registered in registry.ts as `comment-mark` (lazy, toggleable).
- Touch: `frontend/extensions/tiptapComments.ts`, `frontend/extensions/registry.ts`,
  `frontend/pages/editors/tiptap.tsx`
- Tests: `frontend/__tests__/inlineCommentsAndTrackChanges.test.ts`

**Track-changes extension (TipTap TrackChanges)**
- `InsertionMark` (`trackInsertion`): green `<ins>` element with reviewer + changeId attributes.
- `DeletionMark` (`trackDeletion`): red strikethrough `<del>` element with reviewer + changeId attributes.
- `TrackChanges` extension composes both marks and adds `markInsertion`, `markDeletion`,
  `acceptChange`, and `rejectChange` commands.
- Registered in registry.ts as `track-changes` (lazy, toggleable).
- Touch: `frontend/extensions/tiptapTrackChanges.ts`, `frontend/extensions/registry.ts`,
  `frontend/pages/editors/tiptap.tsx`
- Tests: `frontend/__tests__/inlineCommentsAndTrackChanges.test.ts`

**Submit Review inline mark extraction**
- `extractAndPostInlineMarks()` in `tiptap.tsx` walks the live editor document and
  POSTs each `commentMark`, `trackInsertion`, and `trackDeletion` mark to
  `POST /projects/{projectId}/feedback` with `source: "inline"` and `range_anchor: "{from}:{to}"`.
- Uses `Promise.allSettled` — individual POST failures do not abort the submission.
- Touch: `frontend/pages/editors/tiptap.tsx` (lines ~1044–1089)
- Tests: `frontend/__tests__/inlineCommentsAndTrackChanges.test.ts`

**Jump to location**
- Inline feedback rows with `source="inline"` show a "Jump to location" button
  (`data-testid="jump-to-location"`) that reopens the anchored editor position.
- Touch: `frontend/pages/projects/[id]/index.tsx`
- Tests: `frontend/__tests__/projectDocumentPreview.test.tsx`

---

## Item 34 — Federal Style Validator cutover (partial)

**FSV TipTap plugin registered**
- `federal-style-lint` entry added to `frontend/extensions/registry.ts`.
- importPath: `./tiptapFederalStyleLint`, exportName: `federalStyleLint`.
- Tests: `frontend/__tests__/fsvEditorAndProject.test.ts`

**Checker page aligned with FSV visual system (DR-FSV-1 through DR-FSV-12)**
All 12 FSV integration UX tasks completed as of 2026-03-28.

| Item | Title | Files |
|------|-------|-------|
| DR-FSV-1 | Consume shared FSV brand tokens | `frontend/state/branding.ts` |
| DR-FSV-2 | Align checker page with DocReview360 light theme | `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-3 | Match FSV severity colors to system colors | `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-4 | Zero-issues success state | `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-5 | Actionable fix instructions in results display | `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-6 | Per-category collapsible sections with count badges | `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-7 | Loading skeleton while FSV processes | `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-8 | FSV service unavailable banner | `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-9 | Quality score pill semantic colors and labels | `frontend/pages/editors/tiptap.tsx` |
| DR-FSV-10 | Quality pill deep-links to checker page | `frontend/pages/editors/tiptap.tsx`, `frontend/pages/tools/document-quality.tsx` |
| DR-FSV-11 | Consistent "Federal Style Validator" terminology | `frontend/pages/configuration/plugin-marketplace.tsx`, `frontend/pages/tools/document-quality.tsx`, `frontend/pages/tools/index.tsx` |
| DR-FSV-12 | "Test connection" button in admin FSV URL settings | `frontend/pages/tools/index.tsx` |

Tests: `frontend/__tests__/fsvUxTasks.test.ts` (72 source-level tests, all passing).

**Remaining open in item 34:**
- Remove `src/docreview360/regulatory.py` once FSV proxy fully owns regulatory checks.
- Confirm no remaining duplicate style/quality logic.

---

## Accessibility — WCAG 2.1 AA (partial)

**Skip-to-main-content link**
- Implemented in `frontend/pages/_app.tsx` (targets `#main-content`, sr-only until focused).
- Tests: `frontend/__tests__/a11y_skip_link.test.ts`

**Tabs keyboard navigation**
- `ArrowRight/ArrowLeft/Home/End` handling in `frontend/components/ui/tabs.tsx`.
- Active tab `tabIndex=0`, inactive `tabIndex=-1`; panel `aria-labelledby` linkage.
- Tests: `frontend/__tests__/a11y_tabs.test.ts`

**Axe-core scans — public pages**
- Signup, terms, and privacy pages pass axe-core with zero violations.
- Tests: `frontend/__tests__/a11y_public_pages.test.tsx`

**Remaining open for accessibility gate:**
- Axe-core coverage for critical flows (login, project creation, review, approvals, editor).
- Manual AT test with NVDA + Chrome and VoiceOver + Safari (keyboard-only).
- Resolve remaining Pending items in `docs/section508_wcag.md` conformance table.
