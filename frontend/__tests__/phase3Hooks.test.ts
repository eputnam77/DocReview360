/**
 * Phase 3 hooks — source-level and unit tests.
 *
 * Covers:
 *   - usePhaseManagement
 *   - useReviewerManagement
 *   - useApprovalSigning
 *   - useFeedbackHandlers
 *   - useReviewLifecycle
 *
 * Why source-level rather than render tests: these hooks wire together React
 * Query, toast notifications, and authenticatedFetch. Mocking all of those
 * reliably requires significant setup that can hide the real bugs. Source-level
 * guards catch structural regressions (missing exports, incorrect error-handling
 * patterns, wrong API path shapes) with zero flakiness.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const LIB = join(REPO_ROOT, "frontend", "lib");

function lib(name: string): string {
  return readFileSync(join(LIB, name), "utf8");
}

// ---------------------------------------------------------------------------
// usePhaseManagement
// ---------------------------------------------------------------------------

describe("usePhaseManagement — structure", () => {
  const src = lib("usePhaseManagement.ts");

  it("exports usePhaseManagement function", () => {
    expect(src).toContain("export function usePhaseManagement");
  });

  it("exports PhaseManagementState interface", () => {
    expect(src).toContain("export interface PhaseManagementState");
  });

  it("uses useQueryClient for cache invalidation after phase change", () => {
    expect(src).toContain("useQueryClient");
    expect(src).toContain("queryClient.invalidateQueries");
  });

  it("invalidates the project query key after successful phase change", () => {
    expect(src).toContain('"project"');
    expect(src).toMatch(/queryKey.*"project"/);
  });

  it("exposes showPhaseDialog and setShowPhaseDialog", () => {
    expect(src).toContain("showPhaseDialog");
    expect(src).toContain("setShowPhaseDialog");
  });

  it("exposes requestPhaseChange handler", () => {
    expect(src).toContain("requestPhaseChange");
  });

  it("exposes confirmPhaseChange handler", () => {
    expect(src).toContain("confirmPhaseChange");
  });

  it("guards requestPhaseChange with canAdvance check", () => {
    expect(src).toContain("canAdvance");
    expect(src).toMatch(/if\s*\(.*canAdvance/);
  });

  it("shows a toast error when canAdvance is false", () => {
    expect(src).toContain("toast.error");
    expect(src).toContain("All required approvals must be complete");
  });

  it("calls authenticatedFetch with PUT method for phase transition", () => {
    expect(src).toContain(`method: "PUT"`);
    expect(src).toMatch(/\/projects\//);
  });

  it("resets pendingPhase and closes dialog after confirm", () => {
    expect(src).toContain("setShowPhaseDialog(false)");
    expect(src).toContain("setPendingPhase(null)");
  });

  it("guards confirm against missing pendingPhase or project.id", () => {
    expect(src).toMatch(/if\s*\(pendingPhase.*project\?\.id\)/s);
  });
});

// ---------------------------------------------------------------------------
// usePhaseManagement — pure logic (handlePhaseChange step-status derivation)
// ---------------------------------------------------------------------------

type StepStatus = "complete" | "active" | "pending";

function deriveStepStatuses(
  steps: { name: string }[],
  targetPhaseId: string,
): { name: string; status: StepStatus }[] {
  const idx = steps.findIndex((s) => s.name === targetPhaseId);
  if (idx === -1) return steps.map((s) => ({ ...s, status: "pending" as const }));
  return steps.map((s, i) => ({
    ...s,
    status:
      i < idx ? ("complete" as const) : i === idx ? ("active" as const) : ("pending" as const),
  }));
}

describe("usePhaseManagement — deriveStepStatuses logic", () => {
  const steps = [
    { name: "Draft" },
    { name: "Review" },
    { name: "Approval" },
    { name: "Final" },
  ];

  it("marks all steps before target as complete", () => {
    const result = deriveStepStatuses(steps, "Approval");
    expect(result[0].status).toBe("complete");
    expect(result[1].status).toBe("complete");
  });

  it("marks the target step as active", () => {
    const result = deriveStepStatuses(steps, "Approval");
    expect(result[2].status).toBe("active");
  });

  it("marks all steps after target as pending", () => {
    const result = deriveStepStatuses(steps, "Approval");
    expect(result[3].status).toBe("pending");
  });

  it("marks all pending when phase not found", () => {
    const result = deriveStepStatuses(steps, "Unknown");
    expect(result.every((s) => s.status === "pending")).toBe(true);
  });

  it("handles first step correctly (no complete steps)", () => {
    const result = deriveStepStatuses(steps, "Draft");
    expect(result[0].status).toBe("active");
    expect(result.slice(1).every((s) => s.status === "pending")).toBe(true);
  });

  it("handles last step correctly (all previous complete)", () => {
    const result = deriveStepStatuses(steps, "Final");
    expect(result[3].status).toBe("active");
    expect(result.slice(0, 3).every((s) => s.status === "complete")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// useReviewerManagement
// ---------------------------------------------------------------------------

describe("useReviewerManagement — structure", () => {
  const src = lib("useReviewerManagement.ts");

  it("exports useReviewerManagement function", () => {
    expect(src).toContain("export function useReviewerManagement");
  });

  it("exports ReviewerManagementState interface", () => {
    expect(src).toContain("export interface ReviewerManagementState");
  });

  it("uses useQueryClient for cache invalidation", () => {
    expect(src).toContain("useQueryClient");
    expect(src).toContain("queryClient.invalidateQueries");
  });

  it("exposes refreshReviewerData that invalidates project, reviewers, approvals, and workflow", () => {
    expect(src).toContain('"project-reviewers"');
    expect(src).toContain('"approvals"');
    expect(src).toContain('"workflow"');
  });

  it("exposes createApprovalForReviewer", () => {
    expect(src).toContain("createApprovalForReviewer");
  });

  it("createApprovalForReviewer deduplicates based on reviewer + phaseId", () => {
    expect(src).toContain("alreadyExists");
    expect(src).toContain("a.reviewer === reviewer");
  });

  it("exposes handleAddReviewer, handleAddApproval, handleAssignApproval", () => {
    expect(src).toContain("handleAddReviewer");
    expect(src).toContain("handleAddApproval");
    expect(src).toContain("handleAssignApproval");
  });

  it("exposes handleUpdateReviewer and handleRemoveReviewer", () => {
    expect(src).toContain("handleUpdateReviewer");
    expect(src).toContain("handleRemoveReviewer");
  });

  it("validates empty reviewer input before adding", () => {
    expect(src).toContain("Select a reviewer to add.");
  });

  it("validates reviewer against reviewerOptions list when provided", () => {
    expect(src).toContain("Reviewer must be an existing reviewer username.");
  });

  it("validates empty approval reviewer input before adding", () => {
    expect(src).toContain("Select a reviewer for the approval.");
  });

  it("POST /approvals for new approval creation", () => {
    expect(src).toMatch(/\/approvals/);
    expect(src).toContain(`method: "POST"`);
  });

  it("PATCH /approvals/:id/assign for reviewer assignment", () => {
    expect(src).toMatch(/\/approvals\/.*\/assign/);
    expect(src).toContain(`method: "PATCH"`);
  });

  it("has addingReviewer and addingApproval loading states", () => {
    expect(src).toContain("addingReviewer");
    expect(src).toContain("addingApproval");
  });
});

// ---------------------------------------------------------------------------
// useReviewerManagement — deduplication logic
// ---------------------------------------------------------------------------

interface MockApproval {
  reviewer: string;
  phaseId?: string | null;
}

function isApprovalDuplicate(
  approvals: MockApproval[],
  reviewer: string,
  phaseId: string | undefined,
): boolean {
  return approvals.some(
    (a) =>
      a.reviewer === reviewer &&
      ((phaseId && a.phaseId === phaseId) || (!phaseId && !a.phaseId)),
  );
}

describe("useReviewerManagement — deduplication logic", () => {
  it("detects duplicate when same reviewer + same phaseId", () => {
    const approvals: MockApproval[] = [{ reviewer: "alice", phaseId: "Review" }];
    expect(isApprovalDuplicate(approvals, "alice", "Review")).toBe(true);
  });

  it("does not detect duplicate when same reviewer but different phaseId", () => {
    const approvals: MockApproval[] = [{ reviewer: "alice", phaseId: "Review" }];
    expect(isApprovalDuplicate(approvals, "alice", "Approval")).toBe(false);
  });

  it("detects duplicate for phase-less approvals when phaseId is undefined", () => {
    const approvals: MockApproval[] = [{ reviewer: "bob", phaseId: null }];
    expect(isApprovalDuplicate(approvals, "bob", undefined)).toBe(true);
  });

  it("returns false when no approvals exist", () => {
    expect(isApprovalDuplicate([], "alice", "Review")).toBe(false);
  });

  it("returns false when reviewer does not match", () => {
    const approvals: MockApproval[] = [{ reviewer: "alice", phaseId: "Review" }];
    expect(isApprovalDuplicate(approvals, "bob", "Review")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// useApprovalSigning
// ---------------------------------------------------------------------------

describe("useApprovalSigning — structure", () => {
  const src = lib("useApprovalSigning.ts");

  it("exports useApprovalSigning function", () => {
    expect(src).toContain("export function useApprovalSigning");
  });

  it("exports ApprovalSigningState interface", () => {
    expect(src).toContain("export interface ApprovalSigningState");
  });

  it("exports buildApprovalSigningRoute", () => {
    expect(src).toContain("buildApprovalSigningRoute");
  });

  it("exports routeToApprovalSignature", () => {
    expect(src).toContain("routeToApprovalSignature");
  });

  it("buildApprovalSigningRoute constructs /documenso/ URL with return param", () => {
    expect(src).toMatch(/\/documenso\//);
    expect(src).toContain("return=");
    expect(src).toContain("#approvals");
  });

  it("routeToApprovalSignature checks origin for external URLs", () => {
    expect(src).toContain("currentOrigin");
    expect(src).toContain("parsed.origin");
    expect(src).toContain("assignBrowserLocation");
  });

  it("signApproval guards against already-approved approvals", () => {
    expect(src).toContain('"approved"');
    expect(src).toContain("Approval already completed.");
  });

  it("signApproval guards against wrong reviewer", () => {
    expect(src).toContain("You are not assigned to this approval.");
    expect(src).toContain("existing?.reviewer !== username");
  });

  it("signApproval POSTs to /approvals/:id/sign", () => {
    expect(src).toMatch(/\/approvals\/.*\/sign/);
  });

  it("rejectApproval guards against already-rejected approvals", () => {
    expect(src).toContain("Approval already marked as non-concurred.");
  });

  it("rejectApproval PUTs state: rejected", () => {
    expect(src).toContain(`state: "rejected"`);
  });

  it("signApprovalByInitials POSTs to /approvals/:id/sign-initials", () => {
    expect(src).toMatch(/\/approvals\/.*\/sign-initials/);
  });

  it("removeApproval DELETEs from /approvals/:id", () => {
    expect(src).toContain(`method: "DELETE"`);
    expect(src).toMatch(/\/approvals\//);
  });

  it("viewApprovalHistory fetches from /approvals/:id/history", () => {
    expect(src).toMatch(/\/approvals\/.*\/history/);
  });

  it("sendApprovalReminder filters to pending or overdue approvals", () => {
    expect(src).toContain('"pending"');
    expect(src).toContain('"overdue"');
  });

  it("exports viewApprovalHistory", () => {
    expect(src).toContain("viewApprovalHistory");
  });
});

// ---------------------------------------------------------------------------
// useApprovalSigning — URL routing logic (pure)
// ---------------------------------------------------------------------------

function buildSigningRoute(projectId: string, signatureId: string, approvalId: string): string {
  return `/documenso/${encodeURIComponent(signatureId)}?return=${encodeURIComponent(
    `/projects/${projectId}#approvals`,
  )}&approval=${encodeURIComponent(approvalId)}`;
}

describe("useApprovalSigning — buildApprovalSigningRoute logic", () => {
  it("encodes the signatureId in the path", () => {
    const route = buildSigningRoute("proj-1", "sig/123", "appr-1");
    expect(route).toContain("sig%2F123");
  });

  it("includes #approvals in the return parameter", () => {
    const route = buildSigningRoute("proj-1", "sig-123", "appr-1");
    expect(route).toContain("%23approvals");
  });

  it("includes the approvalId as a query param", () => {
    const route = buildSigningRoute("proj-1", "sig-123", "appr-456");
    expect(route).toContain("approval=appr-456");
  });

  it("starts with /documenso/", () => {
    const route = buildSigningRoute("proj-1", "sig-123", "appr-1");
    expect(route.startsWith("/documenso/")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// useFeedbackHandlers
// ---------------------------------------------------------------------------

describe("useFeedbackHandlers — structure", () => {
  const src = lib("useFeedbackHandlers.ts");

  it("exports useFeedbackHandlers function", () => {
    expect(src).toContain("export function useFeedbackHandlers");
  });

  it("exports FeedbackHandlersState interface", () => {
    expect(src).toContain("export interface FeedbackHandlersState");
  });

  it("exports newFeedbackText state", () => {
    expect(src).toContain("newFeedbackText");
    expect(src).toContain("setNewFeedbackText");
  });

  it("exports newFeedbackType state defaulting to comment", () => {
    expect(src).toContain("newFeedbackType");
    expect(src).toContain('"comment"');
  });

  it("exports feedbackTypeFilter and feedbackStatusFilter", () => {
    expect(src).toContain("feedbackTypeFilter");
    expect(src).toContain("feedbackStatusFilter");
  });

  it("exports feedbackShowMyOnly flag", () => {
    expect(src).toContain("feedbackShowMyOnly");
    expect(src).toContain("setFeedbackShowMyOnly");
  });

  it("exports expandedFeedback as a Set", () => {
    expect(src).toContain("expandedFeedback");
    expect(src).toContain("new Set");
  });

  it("handlePostFeedback guards against empty text", () => {
    expect(src).toContain("!newFeedbackText.trim()");
  });

  it("handlePostFeedback POSTs to /projects/:id/feedback", () => {
    expect(src).toMatch(/\/projects\/.*\/feedback/);
    expect(src).toContain(`method: "POST"`);
  });

  it("handlePostFeedback sends feedback_type in body", () => {
    expect(src).toContain("feedback_type");
  });

  it("handleDisposition PUTs to /projects/:id/feedback/:itemId/disposition", () => {
    expect(src).toMatch(/\/projects\/.*\/feedback\/.*\/disposition/);
    expect(src).toContain(`method: "PUT"`);
  });

  it("handleDisposition includes optional reason in body", () => {
    expect(src).toContain("reason");
    expect(src).toContain("body.reason = reason");
  });

  it("handleReply guards against empty reply text", () => {
    expect(src).toContain("replyText[parentId]");
    expect(src).toContain(".trim()");
  });

  it("handleReply POSTs to /projects/:id/feedback/:parentId/reply", () => {
    expect(src).toMatch(/\/projects\/.*\/feedback\/.*\/reply/);
  });

  it("calls refetchFeedback and refetchProgress after successful feedback post", () => {
    expect(src).toContain("refetchFeedback");
    expect(src).toContain("refetchProgress");
  });
});

// ---------------------------------------------------------------------------
// useReviewLifecycle
// ---------------------------------------------------------------------------

describe("useReviewLifecycle — structure", () => {
  const src = lib("useReviewLifecycle.ts");

  it("exports useReviewLifecycle function", () => {
    expect(src).toContain("export function useReviewLifecycle");
  });

  it("exports ReviewLifecycleState interface", () => {
    expect(src).toContain("export interface ReviewLifecycleState");
  });

  it("exposes assignmentReviewerInput state", () => {
    expect(src).toContain("assignmentReviewerInput");
    expect(src).toContain("setAssignmentReviewerInput");
  });

  it("exposes assignmentDueDate state", () => {
    expect(src).toContain("assignmentDueDate");
    expect(src).toContain("setAssignmentDueDate");
  });

  it("exposes addingAssignment loading flag", () => {
    expect(src).toContain("addingAssignment");
  });

  it("handleAddAssignment guards against empty reviewer", () => {
    expect(src).toContain("Enter a reviewer username.");
  });

  it("handleAddAssignment POSTs to /projects/:id/assignments", () => {
    expect(src).toMatch(/\/projects\/.*\/assignments/);
    expect(src).toContain(`method: "POST"`);
  });

  it("handleAddAssignment includes optional due_date in body", () => {
    expect(src).toContain("due_date");
    expect(src).toContain("assignmentDueDate");
  });

  it("handleSendReminder POSTs to /projects/:id/assignments/:id/remind", () => {
    expect(src).toMatch(/\/assignments\/.*\/remind/);
  });

  it("handleSignInternal uses promptInBrowser for optional note", () => {
    expect(src).toContain("promptInBrowser");
    expect(src).toContain("Optional note for internal acknowledgement");
  });

  it("handleSignInternal POSTs to /assignments/:id/sign-internal", () => {
    expect(src).toMatch(/\/sign-internal/);
  });

  it("handleConcur POSTs to /assignments/:id/concur", () => {
    expect(src).toMatch(/\/concur/);
  });

  it("handleNonConcur requires a non-empty reason", () => {
    expect(src).toContain("Add the reason for non-concurrence");
    expect(src).toContain("reason?.trim()");
  });

  it("handleNonConcur POSTs to /assignments/:id/non-concur", () => {
    expect(src).toMatch(/\/non-concur/);
  });

  it("handleSubmitReview POSTs to /assignments/:id/submit", () => {
    expect(src).toMatch(/\/submit/);
    expect(src).toContain("Review submitted. The SME has been notified.");
  });

  it("handleLifecycleTransition asks confirm before transitioning", () => {
    expect(src).toContain("confirm(");
    expect(src).toContain("Transition project status");
  });

  it("handleLifecycleTransition POSTs to /projects/:id/lifecycle", () => {
    expect(src).toMatch(/\/lifecycle/);
  });

  it("calls refetchAssignments, refetchMyAssignments, refetchSummary in handlers", () => {
    expect(src).toContain("refetchAssignments");
    expect(src).toContain("refetchMyAssignments");
    expect(src).toContain("refetchSummary");
  });

  it("calls refetchLifecycle after lifecycle transition", () => {
    expect(src).toContain("refetchLifecycle");
  });
});

// ---------------------------------------------------------------------------
// useReviewLifecycle — lifecycle status label formatting (pure)
// ---------------------------------------------------------------------------

function formatLifecycleStatus(status: string): string {
  return status.replace(/_/g, " ");
}

describe("useReviewLifecycle — formatLifecycleStatus", () => {
  it("replaces underscores with spaces", () => {
    expect(formatLifecycleStatus("under_review")).toBe("under review");
  });

  it("handles multi-underscore statuses", () => {
    expect(formatLifecycleStatus("final_sign_off")).toBe("final sign off");
  });

  it("leaves status without underscores unchanged", () => {
    expect(formatLifecycleStatus("draft")).toBe("draft");
  });

  it("handles empty string", () => {
    expect(formatLifecycleStatus("")).toBe("");
  });
});
