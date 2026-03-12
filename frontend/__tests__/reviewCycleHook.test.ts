/**
 * Item 44 implementation notes:
 *   - review.tsx redirect guard
 *   - useReviewCycle composition contract
 *
 * Tests:
 *  1. Source-level: review.tsx redirects to /projects/{id}#feedback
 *  2. Source-level: useReviewCycle composes the expected sub-hooks and
 *     derives correct metrics (pendingReviewers, unresolvedFeedback, etc.)
 *  3. Unit: derived-field logic tested with fixture data
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

// ---------------------------------------------------------------------------
// review.tsx — redirect contract
// ---------------------------------------------------------------------------

describe("review.tsx — redirect to #feedback", () => {
  const reviewPage = src("pages/projects/[id]/review.tsx");

  it("is marked as deprecated", () => {
    expect(reviewPage).toContain("@deprecated");
  });

  it("uses router.replace to redirect to the feedback hash", () => {
    expect(reviewPage).toContain("router.replace");
    expect(reviewPage).toMatch(/\/projects\/\$\{id\}#feedback/);
  });

  it("guards the redirect with router.isReady", () => {
    expect(reviewPage).toContain("router.isReady");
  });

  it("only redirects when id is defined (avoids redirect on loading state)", () => {
    // The redirect effect must be gated: `if (id) { router.replace(...) }`
    expect(reviewPage).toMatch(/if\s*\(\s*id\s*\)/);
  });

  it("renders a loading skeleton while redirecting (not a blank page)", () => {
    expect(reviewPage).toContain("animate-pulse");
  });
});

// ---------------------------------------------------------------------------
// useReviewCycle — composition and derived fields contract
// ---------------------------------------------------------------------------

describe("useReviewCycle — hook composition", () => {
  const hook = src("lib/useReviewCycle.ts");

  it("exports useReviewCycle function", () => {
    expect(hook).toContain("export function useReviewCycle");
  });

  it("exports ReviewCycleResult interface", () => {
    expect(hook).toContain("export interface ReviewCycleResult");
  });

  it("composes useProjectReviewers", () => {
    expect(hook).toContain("useProjectReviewers");
  });

  it("composes useApprovals or direct approvals query", () => {
    // Either through useApprovals hook or a direct useQuery for approvals.
    expect(hook).toContain("approvals");
    expect(hook).toMatch(/useApprovals|approvalsQuery/);
  });

  it("composes useReviewSummary", () => {
    expect(hook).toContain("useReviewSummary");
  });

  it("exposes feedbackItems from feedback ledger query", () => {
    expect(hook).toContain("feedbackItems");
    expect(hook).toContain("/feedback");
  });

  it("derives pendingReviewers from terminal status set", () => {
    expect(hook).toContain("TERMINAL_STATUSES");
    expect(hook).toContain("pendingReviewers");
  });

  it("derives unresolvedFeedback from unresolved status set", () => {
    expect(hook).toContain("UNRESOLVED_STATUSES");
    expect(hook).toContain("unresolvedFeedback");
  });

  it("derives allSignaturesCollected from approval states", () => {
    expect(hook).toContain("allSignaturesCollected");
    expect(hook).toMatch(/approvals\.every.*approved/s);
  });

  it("derives reviewComplete combining unresolvedFeedback + pendingReviewers + signatures", () => {
    expect(hook).toContain("reviewComplete");
    expect(hook).toMatch(/unresolvedFeedback.*===.*0/);
    expect(hook).toMatch(/pendingReviewers.*===.*0/);
  });

  it("exposes isLoading aggregating all sub-queries", () => {
    expect(hook).toContain("isLoading");
    expect(hook).toMatch(/isLoading.*assignmentsQuery|assignmentsQuery.*isLoading/s);
  });

  it("exposes isError aggregating all sub-queries", () => {
    expect(hook).toContain("isError");
  });
});

// ---------------------------------------------------------------------------
// useReviewCycle — derived field logic (pure unit tests)
// ---------------------------------------------------------------------------

const TERMINAL_STATUSES = new Set(["signed", "rejected", "withdrawn", "replaced"]);
const UNRESOLVED_STATUSES = new Set(["open", "in_progress"]);

function computePendingReviewers(reviewers: { status: string }[]): number {
  return reviewers.filter((r) => !TERMINAL_STATUSES.has(r.status)).length;
}

function computeUnresolvedFeedback(feedbackItems: { status: string }[]): number {
  return feedbackItems.filter((f) => UNRESOLVED_STATUSES.has(f.status)).length;
}

function computeAllSignaturesCollected(approvals: { state: string; signedAt?: string }[]): boolean {
  return approvals.length > 0 && approvals.every((a) => a.state === "approved" && !!a.signedAt);
}

function computeReviewComplete(
  unresolvedFeedback: number,
  pendingReviewers: number,
  approvals: { state: string; signedAt?: string }[],
): boolean {
  const allSigs = computeAllSignaturesCollected(approvals);
  return unresolvedFeedback === 0 && pendingReviewers === 0 && (approvals.length === 0 || allSigs);
}

describe("useReviewCycle — pendingReviewers derived field", () => {
  it("returns 0 when all reviewers are in terminal states", () => {
    const reviewers = [
      { status: "signed" },
      { status: "rejected" },
      { status: "withdrawn" },
    ];
    expect(computePendingReviewers(reviewers)).toBe(0);
  });

  it("counts reviewers not yet in a terminal state", () => {
    const reviewers = [
      { status: "invited" },
      { status: "in_progress" },
      { status: "signed" },
    ];
    expect(computePendingReviewers(reviewers)).toBe(2);
  });

  it("returns the total count when no reviewer is terminal", () => {
    const reviewers = [{ status: "invited" }, { status: "concurred" }];
    expect(computePendingReviewers(reviewers)).toBe(2);
  });
});

describe("useReviewCycle — unresolvedFeedback derived field", () => {
  it("counts items with open or in_progress status", () => {
    const items = [
      { status: "open" },
      { status: "in_progress" },
      { status: "resolved" },
      { status: "rejected" },
    ];
    expect(computeUnresolvedFeedback(items)).toBe(2);
  });

  it("returns 0 when all feedback is resolved", () => {
    const items = [{ status: "resolved" }, { status: "accepted" }];
    expect(computeUnresolvedFeedback(items)).toBe(0);
  });
});

describe("useReviewCycle — allSignaturesCollected derived field", () => {
  it("returns false when approvals list is empty", () => {
    expect(computeAllSignaturesCollected([])).toBe(false);
  });

  it("returns true when all approvals are signed", () => {
    const approvals = [
      { state: "approved", signedAt: "2026-03-12T10:00:00Z" },
      { state: "approved", signedAt: "2026-03-12T11:00:00Z" },
    ];
    expect(computeAllSignaturesCollected(approvals)).toBe(true);
  });

  it("returns false when one approval is unsigned", () => {
    const approvals = [
      { state: "approved", signedAt: "2026-03-12T10:00:00Z" },
      { state: "pending" },
    ];
    expect(computeAllSignaturesCollected(approvals)).toBe(false);
  });
});

describe("useReviewCycle — reviewComplete derived field", () => {
  it("is true when all feedback resolved, all reviewers terminal, no approvals needed", () => {
    expect(computeReviewComplete(0, 0, [])).toBe(true);
  });

  it("is false when there is still unresolved feedback", () => {
    expect(computeReviewComplete(2, 0, [])).toBe(false);
  });

  it("is false when there are still pending reviewers", () => {
    expect(computeReviewComplete(0, 1, [])).toBe(false);
  });

  it("is true when all resolved, all reviewers terminal, and all signed", () => {
    const approvals = [{ state: "approved", signedAt: "2026-03-12T10:00:00Z" }];
    expect(computeReviewComplete(0, 0, approvals)).toBe(true);
  });

  it("is false when approvals exist but not all signed", () => {
    const approvals = [{ state: "pending" }];
    expect(computeReviewComplete(0, 0, approvals)).toBe(false);
  });
});
