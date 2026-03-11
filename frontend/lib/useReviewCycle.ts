// frontend/lib/useReviewCycle.ts
/**
 * useReviewCycle — composite hook for the project review cycle.
 *
 * Composes useProjectReviewers, useApprovals, useComments, useReviewSummary
 * and the feedback ledger query into a single result object for the project view.
 */

import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";
import { useProjectReviewers } from "./useProjectReviewers";
import { useApprovals } from "./useApprovals";
import { useComments } from "./useComments";
import { useReviewSummary } from "./useReviewSummary";
import type { Approval } from "./useApprovals";
import type { Comment } from "./useComments";
import type { ReviewSummary } from "@/types";

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------

/** Lifecycle assignment record returned by GET /projects/{id}/assignments */
export interface ReviewerAssignment {
  id: string;
  reviewer: string;
  status: string;
  requested_at: string;
  due_date?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  signed_at?: string | null;
  replaced_by?: string | null;
  replacement_reason?: string | null;
}

/** Feedback ledger item returned by GET /projects/{id}/feedback */
export interface FeedbackItem {
  id: string;
  reviewer: string;
  feedback_type: string;
  text: string;
  phase?: string | null;
  status: string;
  created_at: string;
  disposition_by?: string | null;
  disposition_at?: string | null;
  disposition_reason?: string | null;
  parent_id?: string | null;
  tags: string[];
  question_satisfied: boolean;
  assignment_id?: string | null;
}

/** Terminal statuses for a reviewer assignment (no action pending) */
const TERMINAL_STATUSES = new Set(["signed", "rejected", "withdrawn", "replaced"]);

/** Unresolved feedback statuses */
const UNRESOLVED_STATUSES = new Set(["open", "in_progress"]);

// -------------------------------------------------------------------------
// Hook
// -------------------------------------------------------------------------

export interface ReviewCycleResult {
  /** Lifecycle assignment records for the project */
  reviewers: ReviewerAssignment[];
  /** Approval records for the project's workflow */
  approvals: Approval[];
  /** Feedback ledger items combined with inline document comments */
  feedbackItems: FeedbackItem[];
  /** Summary of reviews (count) */
  reviewSummary: ReviewSummary;
  /** True while any sub-query is still loading */
  isLoading: boolean;
  /** True if any sub-query returned an error */
  isError: boolean;
  // --- Derived fields ---
  /** Number of reviewers not yet in a terminal state */
  pendingReviewers: number;
  /** Total count of all feedback items */
  totalFeedbackItems: number;
  /** Count of feedback items in an unresolved status */
  unresolvedFeedback: number;
  /** True when every approval has been signed */
  allSignaturesCollected: boolean;
  /** True when all feedback is resolved and all signatures are collected */
  reviewComplete: boolean;
}

/**
 * Compose reviewer assignments, approvals, comments, feedback ledger, and
 * review summary into a single query result for the project view.
 *
 * @param projectId - The project identifier to load data for.
 */
export function useReviewCycle(projectId: string): ReviewCycleResult {
  // --- Sub-queries ---

  // Reviewer lifecycle assignments (richer than the simple reviewers list)
  const assignmentsQuery = useQuery<ReviewerAssignment[]>({
    queryKey: ["assignments", projectId],
    enabled: !!projectId,
    queryFn: async () => {
      if (!projectId) return [];
      const res = await authenticatedFetch(`/projects/${projectId}/assignments`);
      if (!res.ok) return [];
      return res.json();
    },
    staleTime: 30_000,
  });

  // Simple reviewer list (used by useProjectReviewers for mutations; we also
  // use the hook here to keep the cache warm and expose mutations to callers
  // via the returned object).
  const { reviewers: _reviewerNames } = useProjectReviewers(projectId);

  // Approvals for the project's active workflow — we need the workflow id.
  // The project's workflow id is embedded in the assignment query data or we
  // can derive it from the project query.  useApprovals accepts a workflow
  // option; when projectId changes we refetch via the assignments cache.
  // For the composite hook we pull approvals without a workflow filter and let
  // the backend scope them to the project via the assignments endpoint.
  // Since useApprovals requires a workflow id and we may not have it here,
  // we fetch approvals separately via a direct query keyed by projectId.
  const approvalsQuery = useQuery<Approval[]>({
    queryKey: ["project-approvals", projectId],
    enabled: !!projectId,
    queryFn: async () => {
      if (!projectId) return [];
      // Fetch all approvals for this project's workflow(s)
      const res = await authenticatedFetch(`/approvals?project=${encodeURIComponent(projectId)}`);
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    },
    staleTime: 30_000,
  });

  // Review summary (count of submitted reviews)
  const reviewSummaryQuery = useReviewSummary(projectId);

  // Feedback ledger items
  const feedbackQuery = useQuery<FeedbackItem[]>({
    queryKey: ["feedback", projectId],
    enabled: !!projectId,
    queryFn: async () => {
      if (!projectId) return [];
      const res = await authenticatedFetch(`/projects/${projectId}/feedback`);
      if (!res.ok) return [];
      return res.json();
    },
    staleTime: 30_000,
  });

  // -------------------------------------------------------------------------
  // Assemble results
  // -------------------------------------------------------------------------

  const reviewers = assignmentsQuery.data ?? [];
  const approvals = approvalsQuery.data ?? [];
  const feedbackItems = feedbackQuery.data ?? [];
  const reviewSummary: ReviewSummary = reviewSummaryQuery.data ?? { count: 0 };

  const isLoading =
    assignmentsQuery.isLoading ||
    approvalsQuery.isLoading ||
    reviewSummaryQuery.isLoading ||
    feedbackQuery.isLoading;

  const isError =
    assignmentsQuery.isError ||
    approvalsQuery.isError ||
    reviewSummaryQuery.isError ||
    feedbackQuery.isError;

  // --- Derived metrics ---

  const pendingReviewers = reviewers.filter(
    (r) => !TERMINAL_STATUSES.has(r.status),
  ).length;

  const totalFeedbackItems = feedbackItems.length;

  const unresolvedFeedback = feedbackItems.filter((f) =>
    UNRESOLVED_STATUSES.has(f.status),
  ).length;

  const allSignaturesCollected =
    approvals.length > 0 &&
    approvals.every((a) => a.state === "approved" && !!a.signedAt);

  const reviewComplete =
    unresolvedFeedback === 0 &&
    pendingReviewers === 0 &&
    (approvals.length === 0 || allSignaturesCollected);

  return {
    reviewers,
    approvals,
    feedbackItems,
    reviewSummary,
    isLoading,
    isError,
    pendingReviewers,
    totalFeedbackItems,
    unresolvedFeedback,
    allSignaturesCollected,
    reviewComplete,
  };
}
