# Brittleness Findings

Date: 2026-04-16  
Scope: Full codebase — frontend (Next.js/React) and backend (FastAPI/Python)  
Status: Phase 3 frontend extraction complete; findings below cover remaining risk

---

## How to use this document

Each finding has:
- **Severity**: Critical / High / Medium / Low
- **File(s)**: exact path(s)
- **Pattern**: what the code does
- **Risk**: what can go wrong at runtime
- **Task**: what to do about it (numbered for tracking)

Findings are ordered by severity within each section.

---

## Part 1 — Backend

### B-01 · CRITICAL · Global mutable approval state without locks

**File:** `src/docreview360/approvals/core.py` (~line 59)  
**Pattern:** Module-level `approvals: Dict[str, ApprovalModel] = {}` is read and mutated by concurrent async request handlers with no locking.  
**Risk:** Two concurrent requests (e.g., two reviewers approving at the same time) both pass the "not yet approved" guard, both call `_persist_approval()` — last write wins, state machine invariants violated, duplicate approvals possible.  
**Task B-01:** Done (2026-04-17). Introduced a per-approval `asyncio.Lock` around same-ID read-check-write sequences. For distributed deployments, replace with a Redis-backed advisory lock.

---

### B-02 · CRITICAL · Approval state transitions are not atomic

**File:** `src/docreview360/approvals/signatures.py` (~lines 340–468)  
**Pattern:** `update_approval_state()` reads approval from dict, checks current state, then writes back. The read and write are not inside a single lock or transaction.  
**Risk:** Between the "is it already approved?" check and the state write, another request can modify the same record. Immutability contracts for signed approvals can be violated. Sequential workflow ordering checks (preceding steps complete?) are also non-atomic.  
**Task B-02:** Done (2026-04-17). Wrapped the full approval state check-then-write path in the per-approval lock introduced by B-01. A future DB-backed optimistic-locking path remains optional hardening.

---

### B-03 · CRITICAL · Artifact upload failure silently marks approval as complete

**File:** `src/docreview360/approvals/signatures.py` (~lines 384–418)  
**Pattern:** After exhausting upload retries the loop `break`s. The approval is already persisted as `"approved"` in cache and DB, but the PDF/certificate artifact was never uploaded.  
**Risk:** Approvals appear complete in the UI and audit trail with no evidence artifact. Recovery requires manual DB surgery.  
**Task B-03:** Done (2026-04-17). On artifact upload exhaustion the approval now rolls back to its prior state, emits an `approval_upload_failed` error event, and raises a recoverable error instead of silently completing.

---

### B-04 · HIGH · CSRF bypass on cookie-token fallback

**File:** `src/docreview360/auth/_core.py` (~lines 396–401)  
**Pattern:**
```python
if not token and cookie_token:
    _require_csrf_token(request)   # CSRF check only here
    token = cookie_token
elif not token:
    token = cookie_token           # fallback WITHOUT CSRF check
```
**Risk:** The `elif` branch can be reached when `token` is a falsy non-None value (empty string, etc.), allowing cookie auth without CSRF validation.  
**Task B-04:** Done (2026-04-17). Cookie-token fallback now uses a single CSRF-checked path, and tests cover the empty bearer plus valid cookie case.

---

### B-05 · HIGH · Silent lifecycle event exceptions hide audit/integration failures

**Files:** `src/docreview360/api/assignments_router.py`, `documents_router.py`, `projects_router.py`, `feedback_router.py`  
**Pattern:**
```python
try:
    emit_lifecycle_event(event, data)
except Exception:
    pass
```
**Risk:** Audit log entries, webhook deliveries, and downstream integrations silently drop on any exception. Callers have no indication the event was not emitted.  
**Task B-05:** Done (2026-04-17). Lifecycle webhook emitters now log exceptions at `ERROR` instead of silently swallowing them. A dead-letter or at-least-once delivery path remains optional follow-up hardening.

---

### B-06 · HIGH · Approval routing action failures are unlogged

**File:** `src/docreview360/approvals/routing.py` (~lines 29–32)  
**Pattern:**
```python
except Exception:
    return False   # no log, no reraise
```
**Risk:** Approval reassignment and escalation actions fail silently. The workflow appears to complete but the state change did not happen. No diagnostic information survives.  
**Task B-06:** Done (2026-04-17). Approval routing action failures now log exception details at `ERROR` before returning `False`.

---

### B-07 · HIGH · Cache/DB divergence on persist failure

**File:** `src/docreview360/approvals/core.py` (~lines 83–106)  
**Pattern:** `_persist_approval()` catches exceptions and logs a warning, but the in-memory `approvals` dict already holds the new state. The DB write either never committed or is in an unknown state.  
**Risk:** After a DB blip, the process serves the in-memory (modified) state while the DB holds the old state. On restart, the in-memory cache is rebuilt from DB and the change is silently lost.  
**Task B-07:** Done (2026-04-17). Persist failures now restore the pre-change in-memory snapshot, log at `ERROR`, and explicitly `rollback()` the DB session when available.

---

### B-08 · HIGH · N+1 sequential approval validation

**File:** `src/docreview360/approvals/signatures.py` (~lines 344–351)  
**Pattern:** Every state update loops through all values of the module-level `approvals` dict to check that preceding steps are complete. O(n) per request.  
**Risk:** With thousands of approvals the check becomes the dominant cost per state transition. Under high concurrency this compounds with the locking issue above.  
**Task B-08:** Done (2026-04-17). Approvals are now indexed by `(workflow, phase_id)` on create/load/delete so sequential state checks avoid full-dict scans.

---

### B-09 · HIGH · Corrupted audit log entries preserved on parse error

**File:** `src/docreview360/audit.py` (~lines 421–431)  
**Pattern:** Inside the purge loop, a `json.loads` exception is caught but the raw (unparseable) line is still appended to `keep`, so corrupted lines persist across purges.  
**Risk:** Once a corrupted entry enters the audit log it can never be removed by normal purge operations. Log file grows unboundedly with garbage.  
**Task B-09:** Done (2026-04-17). Purge now skips corrupt lines, logs the offending line and offset at `WARNING`, and increments `AUDIT_CORRUPT_LINES_SKIPPED`.

---

### B-10 · HIGH · Silent certificate upload failure loses non-repudiation evidence

**File:** `src/docreview360/integrations/sharepoint_upload.py` (~lines 48–52)  
**Pattern:**
```python
except Exception:
    cert_bytes = b""    # silently falls back to empty
```
**Risk:** Approval certificates are never uploaded to SharePoint. Signed documents lose their non-repudiation artifact with no indication to operators or users.  
**Task B-10:** Done (2026-04-17). Certificate fetch failures are now logged and re-raised so the approval artifact retry policy handles them.

---

### B-11 · HIGH · `api/__init__.py` is 2000+ lines mixing unrelated concerns

**File:** `src/docreview360/api/__init__.py`  
**Pattern:** Rate limiting, branding, WebSocket handlers, file upload, approval endpoints, and project management all live in one file.  
**Risk:** Impossible to reason about error handling scope or side effects across unrelated features. Hard to test in isolation. A change to branding config can accidentally shadow an approval endpoint import.  
**Task B-11:** Done (2026-04-17). Extracted the remaining public and health endpoint groups into `api/public_router.py` and `api/health_router.py`, leaving `api/__init__.py` focused on shared app wiring and WebSocket handlers.

---

### B-12 · MEDIUM · Celery tasks lack idempotency and retry safety

**File:** `src/docreview360/celery_app.py`  
**Pattern:** Tasks registered without `acks_late=True`, `task_reject_on_worker_lost=True`, or idempotency keys.  
**Risk:** Worker crash mid-task causes redelivery; tasks like reminder emails, escalation triggers, and export generation execute twice.  
**Task B-12:** Done (2026-04-17). Added retry-safe Celery registration (`acks_late=True`, `task_reject_on_worker_lost=True`) plus a short-window idempotency cache keyed by task name and args for reminder/escalation execution.

---

### B-13 · MEDIUM · Approval order uniqueness not enforced on creation

**File:** `src/docreview360/approvals/core.py` (~lines 200–235)  
**Pattern:** `create_approval()` accepts `order: int = 0` with no uniqueness check against other approvals in the same workflow/phase.  
**Risk:** Two approvals with `order=1` in the same workflow silently break sequential logic — the preceding-step check passes for both simultaneously.  
**Task B-13:** Done (2026-04-17). `create_approval()` now checks both in-memory and persisted approvals, raises a clear `ValueError` on duplicates, and persists `phase_id` / `approval_order` behind a DB unique index for non-zero sequential steps.

---

### B-14 · MEDIUM · Silent branding config failure serves default without notice

**File:** `src/docreview360/api/__init__.py` (~line 1390)  
**Pattern:** `except Exception: pass` around branding DB load at startup.  
**Risk:** Custom branding silently reverts to defaults on any DB error. Operators have no visibility that their configuration stopped loading.  
**Task B-14:** Done (2026-04-17). Branding load failures now log at `ERROR` and surface through a dedicated `/health/config` endpoint so monitoring can alert on configuration regressions.

---

## Part 2 — Frontend

### F-01 · CRITICAL · `projects/[id]/index.tsx` still 2414 lines

**File:** `frontend/pages/projects/[id]/index.tsx`  
**Pattern:** Despite Phase 3 hook extraction the render section alone is ~1800 lines of inline JSX spanning Approvals, Lifecycle, Feedback, NARA, SLA, Audit, and version drawer tabs.  
**Risk:** Any error in one tab's render path crashes the entire page. Impossible to lazy-load or code-split individual sections. State shared across unrelated sections causes cascade re-renders.  
**Task F-01:** Done (2026-04-17). Extracted the project-detail tab shells into dedicated files under `components/project/` (`ApprovalsTab`, `LifecycleTab`, `FeedbackTab`, `NaraTab`, `SlaTab`, `AuditTab`) so the page no longer owns every section wrapper inline.
- `ApprovalsTab.tsx`
- `LifecycleTab.tsx`
- `FeedbackTab.tsx`
- `NaraTab.tsx`
- `SlaTab.tsx`
- `AuditTab.tsx`

Wrap each in a local `ErrorBoundary` so a crash in one tab doesn't unmount the others.

---

### F-02 · HIGH · `useProjectPageData.ts` orchestrates 10+ queries in one hook (619 lines)

**File:** `frontend/lib/useProjectPageData.ts`  
**Pattern:** Single hook owns: project, workflow, approvals, reviewers, assignments, SLA summary, SLA deadlines, lifecycle, feedback, progress, versions, NARA — plus derived state and eligibility-cache effects.  
**Risk:** A stale-time change or enabled-condition bug in one query can silently break unrelated data. 20+ return values create an implicit contract that's hard to evolve. Dependent effects re-run on unrelated data changes.  
**Task F-02:** Done (2026-04-17). Split project-detail query orchestration into concern-scoped hooks in `projectPageDataHooks.ts` (`useProjectReviewCycleData`, `useProjectFeedbackData`, `useProjectDocumentScores`, `useProjectVersionHistory`, `useProjectFSVStatus`) while preserving the page-level return contract.
- `useProjectCore.ts` — project, workflow, approvals, reviewers
- `useProjectAssignments.ts` — assignments, my-assignments, summary, lifecycle
- `useProjectFeedback.ts` — feedback, progress, versions
- `useProjectSla.ts` — SLA summary, deadlines
- `useProjectNara.ts` — NARA fields, load/save

---

### F-03 · HIGH · `useEditorExtensions.ts` manages 9 independent extension lifecycles (448 lines)

**File:** `frontend/lib/useEditorExtensions.ts`  
**Pattern:** One hook manages collab (Y.js + HocuspocusProvider), lint, heading-lock, indentation, section-node, mark-review, watermark, comment-mark, and track-changes — all with their own status states and toggle handlers.  
**Risk:** Dynamic import failures for any one extension crash the entire hook. Preference persistence re-runs when any of the 9 extension states changes, causing excessive API calls.  
**Task F-03:** Done (2026-04-17). Extracted editor extension state management into `useEditorCollab.ts`, `useEditorLint.ts`, and `useEditorOptionalExtensions.ts` so independent extension failures and toggles are isolated.
- `useEditorCollab.ts` — Y.js + Hocuspocus lifecycle
- `useEditorLint.ts` — lint extension load/toggle
- `useEditorOptionalExtensions.ts` — heading-lock, indentation, section-node, mark-review, watermark

Each sub-hook can fail independently without taking down the editor.

---

### F-04 · HIGH · No error boundaries around crash-prone page sections

**Files:** `frontend/pages/projects/[id]/index.tsx`, `frontend/pages/editors/tiptap.tsx`  
**Pattern:** `_app.tsx` has a top-level `PageErrorBoundary` but no section-level boundaries. A crash in the ApprovalTable, the TipTap editor, or the SLA panel takes down the entire page.  
**Risk:** Single component failure = full white screen. Users lose all context and unsaved work.  
**Task F-04:** Done (2026-04-17). Added `SectionErrorBoundary` wrappers around the lazy TipTap editor entrypoint and the crash-prone project page sections (approvals, SLA summary, audit timeline) so a local render failure no longer whitescreens the full page.

---

### F-05 · HIGH · `ApprovalTable` has 12 props including 8 callback functions

**File:** `frontend/components/ApprovalTable.tsx`  
**Pattern:** Component receives `onSign`, `onReject`, `onSignInitials`, `onReset`, `onRemove`, `onBulkReminder`, `onHistory`, `onAssign` as individual props.  
**Risk:** Adding a new action requires threading a new prop through every layer between the projects page and this component. Re-renders propagate on every parent render because callback identity is unstable.  
**Task F-05:** Done (2026-04-17). Consolidated the approval row callbacks behind a typed `handlers: ApprovalHandlers` prop and updated the project page call sites to pass a single handler object instead of threading each callback separately.

---

### F-06 · HIGH · `saveRevision` doesn't guard against unmounted component

**File:** `frontend/lib/useEditorSave.ts` (~lines 53–126)  
**Pattern:** `saveRevision` schedules a `setTimeout` and then calls `setSaveStatus`, `setPdfUrl`, `setValidationSummary` from inside an async callback. No mounted-check before state setters.  
**Risk:** If the user navigates away during an active debounce window, state setters fire on an unmounted component — memory leak + React warning in strict mode, silent state corruption in production.  
**Task F-06:** Done (2026-04-17). Added an `isMounted` ref plus unmount cleanup in `useEditorSave`, and guarded save-status, PDF URL, and validation-summary state updates behind mounted checks.

---

### F-07 · HIGH · API response shapes assumed without null-checks

**Files:** `frontend/lib/useReviewerManagement.ts` (~lines 107–118), `frontend/pages/projects/[id]/index.tsx` (~lines 270–279)  
**Pattern:** After a successful fetch, fields like `created.id`, `created.reviewer`, `d.details?.approvalId` are accessed without checking if the response actually contains them.  
**Risk:** Backend field rename or versioning change causes `undefined` to be stored in state, leading to downstream render crashes or silent data loss.  
**Task F-07:** Done (2026-04-17). Added response-shape guards around approval creation and kept the project audit-log mapping on optional chaining / null-coalescing paths so malformed responses fail loudly instead of storing `undefined` state.

---

### F-08 · HIGH · `document-types.tsx` configuration page is 983 lines with unguarded async

**File:** `frontend/pages/configuration/document-types.tsx`  
**Pattern:** Three parallel `authenticatedFetch` calls in a `useEffect` with `.catch(() => setPhases([]))` — errors silently produce empty lists. No loading spinner while fetches are in flight.  
**Risk:** Users see a blank form with no indication that the backend failed. They may submit the form thinking it's blank by design.  
**Task F-08:** Done (2026-04-17). Converted the document-types configuration page to three dedicated React Query hooks (`document-types`, `phases`, `workflow-templates`), preserved the loading skeleton and inline retryable error state, and wired retry to refetch all three queries together.

---

### F-09 · MEDIUM · `useProjectPageData` "best-effort" fetch swallows errors silently

**File:** `frontend/lib/useProjectPageData.ts` (~line 364)  
**Pattern:** `.catch(() => {})` on the assignment view-tracking POST.  
**Risk:** If the view-tracking endpoint is down or returns 500, the failure is invisible — no log, no user feedback, and no retry. Engagement analytics are silently zeroed.  
**Task F-09:** Done (2026-04-17). Replaced the silent best-effort assignment-view tracking catch with a labeled `console.warn` so failures show up during browser-side incident investigation.

---

### F-10 · MEDIUM · `useEditorTemplates` outside-click handler may accumulate if `showTemplatePicker` toggles rapidly

**File:** `frontend/lib/useEditorTemplates.ts` (~lines 81–91)  
**Pattern:** `useEffect` adds a `mousedown` listener when `showTemplatePicker` becomes true, removes it on cleanup. If the state toggles fast (double-click), React may batch-fire the effect before cleanup runs.  
**Risk:** Multiple simultaneous listeners; picker closes immediately after opening because a stale listener fires.  
**Task F-10:** Done (2026-04-17). Added `pickerListenerRef` tracking in `useEditorTemplates` so the previous outside-click handler is removed before a new one is attached, preventing listener accumulation on rapid toggles.

---

### F-11 · MEDIUM · Dead state: `versions` initialized but never populated

**File:** `frontend/pages/projects/[id]/index.tsx` (~line 134)  
**Pattern:** `const [versions] = useState<VersionEntry[]>([]);` — setter is never used in the current file.  
**Risk:** The version drawer always shows empty list. This is either broken functionality or leftover from the Phase 3 extraction (the setter may have been dropped when the query was moved to `useProjectPageData`).  
**Task F-11:** Done (2026-04-17). Removed the dead local versions state from the project page and now consume `versions` directly from `useProjectPageData`.

---

### F-12 · MEDIUM · `console.error` in hooks leaks internal state to production logs

**Files:** `frontend/lib/usePhaseManagement.ts` (~line 78), `frontend/lib/useReviewerManagement.ts` (~lines 235, 245)  
**Pattern:** `console.error(error)` called directly in catch blocks.  
**Risk:** Error objects with stack traces and potentially user-identifiable information appear in browser consoles in production. No structured log format.  
**Task F-12:** Done (2026-04-17). Replaced the direct hook-level error dumping in `usePhaseManagement` / `useReviewerManagement` with user-facing toasts plus labeled `console.warn` diagnostics.

---

### F-13 · MEDIUM · Configuration pages lack loading states (3 additional pages)

**Files:** `frontend/pages/configuration/phases.tsx`, `frontend/pages/configuration/permissions.tsx`, `frontend/pages/configuration/workflows/new.tsx`  
**Pattern:** `useEffect` + raw fetch populates state; no loading flag set, no error displayed.  
**Risk:** Users interact with stale or empty forms while background fetches are still in flight.  
**Task F-13:** Done (2026-04-17). Added explicit `isLoading` / `fetchError` states, loading skeletons, and retry affordances to `configuration/phases.tsx`, `configuration/permissions.tsx`, and `configuration/workflows/new.tsx`.

---

### F-14 · LOW · `id as string` cast before router.isReady check is fully settled

**File:** `frontend/pages/projects/[id]/index.tsx` (~line 188)  
**Pattern:** `useProject(id as string)` where `id` comes from `router.isReady ? router.query.id : undefined`. The `as string` cast bypasses TypeScript's `string | string[] | undefined` type.  
**Risk:** If router returns an array for `id` (e.g., `/projects/foo/bar`), `useProject` receives an array silently cast to string, producing a malformed URL.  
**Task F-14:** Done (2026-04-17). Removed the unsafe `router.query.id as string` cast, derived `safeId` from the raw route param, and threaded that guarded value through the project detail hooks and route-dependent links.

---

### F-15 · LOW · Unbounded approval list rendering without virtualization

**File:** `frontend/components/ApprovalTable.tsx`  
**Pattern:** All filtered approvals are rendered as DOM rows without windowing. `reviews/[reviewId].tsx` already uses `FixedSizeList` correctly as a reference.  
**Risk:** With 100+ approvals the table causes visible jank and high memory usage.  
**Task F-15:** Done (2026-04-17). Added a `react-window` virtualization path to `ApprovalTable` so large filtered approval sets render through a `FixedSizeList` instead of a full DOM row expansion.

---

## Summary

All brittleness findings in this document are implemented and verified as of **2026-04-17**.
