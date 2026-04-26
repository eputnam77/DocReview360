# Project Page Overview Cleanup

Two targeted layout changes to `frontend/pages/projects/[id]/index.tsx`.
No logic changes — pure JSX reordering and a section move.

---

## Change 1 — Move NARA out of Overview to its own bottom section

**Problem:** The NARA/Records Retention form is buried inside the `#overview` section
(~line 1041). It only gets filled out late in the document lifecycle, so it makes Overview
unnecessarily long and cluttered for users who are nowhere near records submission.

**Steps:**
1. Delete the `{canEdit && (<NaraTab>...<Disclosure>...</Disclosure></NaraTab>)}` block
   from inside `#overview` (currently between Quality Scores and the Primary CTA).
2. After the `</AuditTab>` closing tag (~line 2384), add a new standalone section that
   wraps the same NARA form JSX, gated by `canEdit`. Keep it inside a `<NaraTab>` wrapper
   so the existing tab visibility logic is preserved.

**Result:** Section order becomes:
- Overview → Approvals → Reviewers → Comments → Audit History → Records Retention (NARA)

---

## Change 2 — Reorder items within Overview

**Problem:** The current Overview order puts Lifecycle and SLA *above* the Workflow/Progress
grid. Users see phase-blocker details before seeing the basic "where is this in the workflow"
picture. The more useful reading order flows from high-level to detail.

**Current order inside `#overview`:**
1. Project Details (Disclosure)
2. KpiCards
3. Project Lifecycle Status card
4. Review SLA Status
5. Document Quality Scores
6. Workflow & Progress grid (2-col)
7. NARA (being removed — see Change 1)
8. Primary CTA

**Target order:**
1. Project Details (Disclosure)
2. KpiCards
3. Workflow & Progress grid ← moved up
4. Project Lifecycle Status card
5. Review SLA Status
6. Document Quality Scores
7. Primary CTA

**Steps:**
1. Cut the `{/* Workflow & progress */}` block (~lines 1005–1039).
2. Paste it immediately after the `<KpiCards stats={stats} />` line (~line 812),
   before the `{lifecycleRecord && ...}` Lifecycle card block.

---

## Verification

After both changes:
- `npm run build` (frontend) should pass with no new errors.
- `npm test` should remain green (pure JSX ordering, no hook or logic changes).
- Visually: NARA no longer appears inside Overview; Workflow/Progress appears near the top
  of Overview above Lifecycle and SLA.
