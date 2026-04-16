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
**Task B-01:** Introduce an `asyncio.Lock` per approval ID (or a global write lock) around all read-check-write sequences. For distributed deployments, replace with a Redis-backed advisory lock.

---

### B-02 · CRITICAL · Approval state transitions are not atomic

**File:** `src/docreview360/approvals/signatures.py` (~lines 340–468)  
**Pattern:** `update_approval_state()` reads approval from dict, checks current state, then writes back. The read and write are not inside a single lock or transaction.  
**Risk:** Between the "is it already approved?" check and the state write, another request can modify the same record. Immutability contracts for signed approvals can be violated. Sequential workflow ordering checks (preceding steps complete?) are also non-atomic.  
**Task B-02:** Wrap the entire check-then-write block in the per-approval lock introduced by B-01. Consider moving state authority to the database row with optimistic locking (`version` column + `UPDATE … WHERE version = ?`).

---

### B-03 · CRITICAL · Artifact upload failure silently marks approval as complete

**File:** `src/docreview360/approvals/signatures.py` (~lines 384–418)  
**Pattern:** After exhausting upload retries the loop `break`s. The approval is already persisted as `"approved"` in cache and DB, but the PDF/certificate artifact was never uploaded.  
**Risk:** Approvals appear complete in the UI and audit trail with no evidence artifact. Recovery requires manual DB surgery.  
**Task B-03:** On artifact upload exhaustion, roll the approval state back to `"pending"` (or a new `"signature_pending_upload"` state), emit an alert event, and surface a recoverable error to the user rather than silently completing.

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
**Task B-04:** Consolidate cookie-token handling into a single code path. CSRF validation must be applied whenever `cookie_token` is used regardless of how the `elif` is reached. Add a test that sends a request with an empty bearer string and a valid cookie to verify CSRF is required.

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
**Task B-05:** Replace bare `except: pass` with `except Exception as exc: logger.error("lifecycle event failed", exc_info=exc)`. Consider a dead-letter queue or at-least-once delivery for critical events (approval signed, project submitted).

---

### B-06 · HIGH · Approval routing action failures are unlogged

**File:** `src/docreview360/approvals/routing.py` (~lines 29–32)  
**Pattern:**
```python
except Exception:
    return False   # no log, no reraise
```
**Risk:** Approval reassignment and escalation actions fail silently. The workflow appears to complete but the state change did not happen. No diagnostic information survives.  
**Task B-06:** Log exception details at `ERROR` level before returning `False`. Callers should check the return value and surface an error rather than assuming success.

---

### B-07 · HIGH · Cache/DB divergence on persist failure

**File:** `src/docreview360/approvals/core.py` (~lines 83–106)  
**Pattern:** `_persist_approval()` catches exceptions and logs a warning, but the in-memory `approvals` dict already holds the new state. The DB write either never committed or is in an unknown state.  
**Risk:** After a DB blip, the process serves the in-memory (modified) state while the DB holds the old state. On restart, the in-memory cache is rebuilt from DB and the change is silently lost.  
**Task B-07:** On persist failure, revert the in-memory state to the pre-change value (keep a copy before mutation). Log at `ERROR`. For the DB session, ensure explicit `rollback()` is called in the exception handler.

---

### B-08 · HIGH · N+1 sequential approval validation

**File:** `src/docreview360/approvals/signatures.py` (~lines 344–351)  
**Pattern:** Every state update loops through all values of the module-level `approvals` dict to check that preceding steps are complete. O(n) per request.  
**Risk:** With thousands of approvals the check becomes the dominant cost per state transition. Under high concurrency this compounds with the locking issue above.  
**Task B-08:** Pre-index approvals by `(workflow, phase_id)` on load/create. The sequential check then becomes an O(1) lookup. Alternatively, push this constraint to a DB query with a covering index.

---

### B-09 · HIGH · Corrupted audit log entries preserved on parse error

**File:** `src/docreview360/audit.py` (~lines 421–431)  
**Pattern:** Inside the purge loop, a `json.loads` exception is caught but the raw (unparseable) line is still appended to `keep`, so corrupted lines persist across purges.  
**Risk:** Once a corrupted entry enters the audit log it can never be removed by normal purge operations. Log file grows unboundedly with garbage.  
**Task B-09:** On parse exception, skip the line (do not append to `keep`), log at `WARNING` with the line content and offset, and increment a `AUDIT_CORRUPT_LINES_SKIPPED` metric counter.

---

### B-10 · HIGH · Silent certificate upload failure loses non-repudiation evidence

**File:** `src/docreview360/integrations/sharepoint_upload.py` (~lines 48–52)  
**Pattern:**
```python
except Exception:
    cert_bytes = b""    # silently falls back to empty
```
**Risk:** Approval certificates are never uploaded to SharePoint. Signed documents lose their non-repudiation artifact with no indication to operators or users.  
**Task B-10:** Raise the exception (or re-raise after logging). Propagate the failure up to `_upload_approval_artifacts` so the retry policy in B-03 applies to certificate upload as well as document upload.

---

### B-11 · HIGH · `api/__init__.py` is 2000+ lines mixing unrelated concerns

**File:** `src/docreview360/api/__init__.py`  
**Pattern:** Rate limiting, branding, WebSocket handlers, file upload, approval endpoints, and project management all live in one file.  
**Risk:** Impossible to reason about error handling scope or side effects across unrelated features. Hard to test in isolation. A change to branding config can accidentally shadow an approval endpoint import.  
**Task B-11:** Decompose by concern into sub-routers already partially started (`assignments_router`, `documents_router`, etc.). Move remaining inline endpoint groups to dedicated router files. Target: no router file over 300 lines.

---

### B-12 · MEDIUM · Celery tasks lack idempotency and retry safety

**File:** `src/docreview360/celery_app.py`  
**Pattern:** Tasks registered without `acks_late=True`, `task_reject_on_worker_lost=True`, or idempotency keys.  
**Risk:** Worker crash mid-task causes redelivery; tasks like reminder emails, escalation triggers, and export generation execute twice.  
**Task B-12:** Add `acks_late=True` to tasks that mutate state. Add idempotency keys (hash of task args + execution window) checked against a short-TTL cache before executing the task body.

---

### B-13 · MEDIUM · Approval order uniqueness not enforced on creation

**File:** `src/docreview360/approvals/core.py` (~lines 200–235)  
**Pattern:** `create_approval()` accepts `order: int = 0` with no uniqueness check against other approvals in the same workflow/phase.  
**Risk:** Two approvals with `order=1` in the same workflow silently break sequential logic — the preceding-step check passes for both simultaneously.  
**Task B-13:** On creation, query approvals for the workflow+phase and assert the new `order` value is unique. Raise `ValueError` with a clear message if not. Add a DB unique constraint on `(workflow_id, phase_id, order)`.

---

### B-14 · MEDIUM · Silent branding config failure serves default without notice

**File:** `src/docreview360/api/__init__.py` (~line 1390)  
**Pattern:** `except Exception: pass` around branding DB load at startup.  
**Risk:** Custom branding silently reverts to defaults on any DB error. Operators have no visibility that their configuration stopped loading.  
**Task B-14:** Log at `ERROR` on exception. Expose a `/health/config` endpoint (or add to existing `/health`) that returns branding config load status so monitoring can alert on it.

---

## Part 2 — Frontend

### F-01 · CRITICAL · `projects/[id]/index.tsx` still 2414 lines

**File:** `frontend/pages/projects/[id]/index.tsx`  
**Pattern:** Despite Phase 3 hook extraction the render section alone is ~1800 lines of inline JSX spanning Approvals, Lifecycle, Feedback, NARA, SLA, Audit, and version drawer tabs.  
**Risk:** Any error in one tab's render path crashes the entire page. Impossible to lazy-load or code-split individual sections. State shared across unrelated sections causes cascade re-renders.  
**Task F-01:** Extract each major tab section into a dedicated component file under `components/project/`:
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
**Task F-02:** Split into concern-scoped hooks:
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
**Task F-03:** Extract into focused sub-hooks:
- `useEditorCollab.ts` — Y.js + Hocuspocus lifecycle
- `useEditorLint.ts` — lint extension load/toggle
- `useEditorOptionalExtensions.ts` — heading-lock, indentation, section-node, mark-review, watermark

Each sub-hook can fail independently without taking down the editor.

---

### F-04 · HIGH · No error boundaries around crash-prone page sections

**Files:** `frontend/pages/projects/[id]/index.tsx`, `frontend/pages/editors/tiptap.tsx`  
**Pattern:** `_app.tsx` has a top-level `PageErrorBoundary` but no section-level boundaries. A crash in the ApprovalTable, the TipTap editor, or the SLA panel takes down the entire page.  
**Risk:** Single component failure = full white screen. Users lose all context and unsaved work.  
**Task F-04:** Add `<SectionErrorBoundary>` wrappers (a thin reusable component with a "This section failed to load" fallback) around:
- The TipTap editor in `tiptap.tsx`
- The Approvals section in the projects page
- The SLA panel
- The Audit timeline

---

### F-05 · HIGH · `ApprovalTable` has 12 props including 8 callback functions

**File:** `frontend/components/ApprovalTable.tsx`  
**Pattern:** Component receives `onSign`, `onReject`, `onSignInitials`, `onReset`, `onRemove`, `onBulkReminder`, `onHistory`, `onAssign` as individual props.  
**Risk:** Adding a new action requires threading a new prop through every layer between the projects page and this component. Re-renders propagate on every parent render because callback identity is unstable.  
**Task F-05:** Replace individual callback props with a single `handlers: ApprovalHandlers` object prop (typed interface). All callbacks are stable from `useApprovalSigning` already — pass the whole return value. Reduces prop count from 12 to ~5.

---

### F-06 · HIGH · `saveRevision` doesn't guard against unmounted component

**File:** `frontend/lib/useEditorSave.ts` (~lines 53–126)  
**Pattern:** `saveRevision` schedules a `setTimeout` and then calls `setSaveStatus`, `setPdfUrl`, `setValidationSummary` from inside an async callback. No mounted-check before state setters.  
**Risk:** If the user navigates away during an active debounce window, state setters fire on an unmounted component — memory leak + React warning in strict mode, silent state corruption in production.  
**Task F-06:** Add an `isMounted` ref (set `false` in the `useEffect` cleanup that returns `() => { isMounted.current = false }`). Guard all `setSaveStatus`, `setPdfUrl`, `setValidationSummary` calls with `if (isMounted.current)`.

---

### F-07 · HIGH · API response shapes assumed without null-checks

**Files:** `frontend/lib/useReviewerManagement.ts` (~lines 107–118), `frontend/pages/projects/[id]/index.tsx` (~lines 270–279)  
**Pattern:** After a successful fetch, fields like `created.id`, `created.reviewer`, `d.details?.approvalId` are accessed without checking if the response actually contains them.  
**Risk:** Backend field rename or versioning change causes `undefined` to be stored in state, leading to downstream render crashes or silent data loss.  
**Task F-07:** Define explicit TypeScript interfaces for all API response shapes (or use `zod` for runtime validation at fetch boundaries). At minimum, add a guard: `if (!created?.id) throw new Error("Unexpected response shape from POST /approvals")`.

---

### F-08 · HIGH · `document-types.tsx` configuration page is 983 lines with unguarded async

**File:** `frontend/pages/configuration/document-types.tsx`  
**Pattern:** Three parallel `authenticatedFetch` calls in a `useEffect` with `.catch(() => setPhases([]))` — errors silently produce empty lists. No loading spinner while fetches are in flight.  
**Risk:** Users see a blank form with no indication that the backend failed. They may submit the form thinking it's blank by design.  
**Task F-08:** (a) Convert the three parallel fetches to React Query hooks so loading/error states are automatic. (b) Show a loading skeleton while in-flight. (c) Show an inline error message (not just empty state) when a fetch fails.

---

### F-09 · MEDIUM · `useProjectPageData` "best-effort" fetch swallows errors silently

**File:** `frontend/lib/useProjectPageData.ts` (~line 364)  
**Pattern:** `.catch(() => {})` on the assignment view-tracking POST.  
**Risk:** If the view-tracking endpoint is down or returns 500, the failure is invisible — no log, no user feedback, and no retry. Engagement analytics are silently zeroed.  
**Task F-09:** Replace `.catch(() => {})` with `.catch((err) => console.warn("view tracking failed", err))`. Treat as best-effort but at least log so it shows up in browser DevTools during incident investigation.

---

### F-10 · MEDIUM · `useEditorTemplates` outside-click handler may accumulate if `showTemplatePicker` toggles rapidly

**File:** `frontend/lib/useEditorTemplates.ts` (~lines 81–91)  
**Pattern:** `useEffect` adds a `mousedown` listener when `showTemplatePicker` becomes true, removes it on cleanup. If the state toggles fast (double-click), React may batch-fire the effect before cleanup runs.  
**Risk:** Multiple simultaneous listeners; picker closes immediately after opening because a stale listener fires.  
**Task F-10:** Use a `useRef` to track and explicitly remove the previous handler before adding a new one, or debounce the toggle with a short delay (16ms) to prevent double-firing.

---

### F-11 · MEDIUM · Dead state: `versions` initialized but never populated

**File:** `frontend/pages/projects/[id]/index.tsx` (~line 134)  
**Pattern:** `const [versions] = useState<VersionEntry[]>([]);` — setter is never used in the current file.  
**Risk:** The version drawer always shows empty list. This is either broken functionality or leftover from the Phase 3 extraction (the setter may have been dropped when the query was moved to `useProjectPageData`).  
**Task F-11:** Wire up `versions` from `useProjectPageData` destructuring (it's already returned there as `versions`). Remove the dead local `useState`.

---

### F-12 · MEDIUM · `console.error` in hooks leaks internal state to production logs

**Files:** `frontend/lib/usePhaseManagement.ts` (~line 78), `frontend/lib/useReviewerManagement.ts` (~lines 235, 245)  
**Pattern:** `console.error(error)` called directly in catch blocks.  
**Risk:** Error objects with stack traces and potentially user-identifiable information appear in browser consoles in production. No structured log format.  
**Task F-12:** Replace raw `console.error(error)` with `toast.error("...")`  (already used for user-facing messages) and structured `console.warn` for dev-only diagnostics. Consider a central `reportError(err)` utility that strips sensitive fields and can be wired to an error tracking service.

---

### F-13 · MEDIUM · Configuration pages lack loading states (3 additional pages)

**Files:** `frontend/pages/configuration/phases.tsx`, `frontend/pages/configuration/permissions.tsx`, `frontend/pages/configuration/workflows/new.tsx`  
**Pattern:** `useEffect` + raw fetch populates state; no loading flag set, no error displayed.  
**Risk:** Users interact with stale or empty forms while background fetches are still in flight.  
**Task F-13:** Apply the same pattern used on the working pages — either React Query or an explicit `isLoading` boolean — and render a loading skeleton before data arrives.

---

### F-14 · LOW · `id as string` cast before router.isReady check is fully settled

**File:** `frontend/pages/projects/[id]/index.tsx` (~line 188)  
**Pattern:** `useProject(id as string)` where `id` comes from `router.isReady ? router.query.id : undefined`. The `as string` cast bypasses TypeScript's `string | string[] | undefined` type.  
**Risk:** If router returns an array for `id` (e.g., `/projects/foo/bar`), `useProject` receives an array silently cast to string, producing a malformed URL.  
**Task F-14:** Replace `id as string` with `typeof id === "string" ? id : undefined` and pass that to the hook.

---

### F-15 · LOW · Unbounded approval list rendering without virtualization

**File:** `frontend/components/ApprovalTable.tsx`  
**Pattern:** All filtered approvals are rendered as DOM rows without windowing. `reviews/[reviewId].tsx` already uses `FixedSizeList` correctly as a reference.  
**Risk:** With 100+ approvals the table causes visible jank and high memory usage.  
**Task F-15:** Add `react-window` `FixedSizeList` to `ApprovalTable` (already a dependency from the reviews page). Virtualize rows when `approvals.length > 50`.

---

## Summary by priority

### Do first (Critical + immediate risk)

| ID | Area | File |
|----|------|------|
| B-01 | Approval state race condition — no locking | `approvals/core.py` |
| B-02 | Approval state transition not atomic | `approvals/signatures.py` |
| B-03 | Artifact upload failure silently completes approval | `approvals/signatures.py` |
| B-04 | CSRF bypass on cookie-token fallback | `auth/_core.py` |
| F-06 | `saveRevision` fires state setters after unmount | `lib/useEditorSave.ts` |
| F-11 | Dead `versions` state — version drawer always empty | `pages/projects/[id]/index.tsx` |

### Do next (High — production stability)

| ID | Area | File |
|----|------|------|
| B-05 | Silent lifecycle event exception loss | Multiple routers |
| B-06 | Approval routing failures unlogged | `approvals/routing.py` |
| B-07 | Cache/DB divergence on persist failure | `approvals/core.py` |
| B-08 | N+1 sequential approval validation | `approvals/signatures.py` |
| B-09 | Corrupted audit log entries never purged | `audit.py` |
| B-10 | Silent certificate upload failure | `integrations/sharepoint_upload.py` |
| B-11 | `api/__init__.py` 2000+ lines monolith | `api/__init__.py` |
| F-01 | Projects page still 2414 lines — tab extraction | `pages/projects/[id]/index.tsx` |
| F-02 | `useProjectPageData` 619 lines — split by concern | `lib/useProjectPageData.ts` |
| F-04 | No section-level error boundaries | Projects page, editor page |
| F-05 | `ApprovalTable` 12-prop drilling | `components/ApprovalTable.tsx` |
| F-07 | API response shapes unvalidated | Multiple hooks |
| F-08 | `document-types.tsx` unguarded async + no loading state | `pages/configuration/document-types.tsx` |

### Backlog (Medium / Low)

| ID | Area |
|----|------|
| B-12 | Celery task idempotency |
| B-13 | Approval order uniqueness enforcement |
| B-14 | Silent branding config failure |
| F-03 | `useEditorExtensions` split by concern |
| F-09 | Best-effort fetch silent swallow |
| F-10 | Template picker outside-click listener race |
| F-12 | `console.error` in production hooks |
| F-13 | Config page loading states |
| F-14 | `id as string` cast |
| F-15 | ApprovalTable virtualization |
