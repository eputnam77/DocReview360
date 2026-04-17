// frontend/lib/useProjectPageData.ts
// Encapsulates all secondary useQuery calls and derived computed values for the
// project detail page that are NOT covered by useProject/usePhases/useApprovals
// /useProjectReviewers/useReviewSummary.

import { useQuery } from "@tanstack/react-query";
import React, { useMemo, useEffect } from "react";
import { authenticatedFetch } from "@/lib/api";
import type { Approval, LogEntry, Project, Workflow, VersionEntry } from "@/components/project/_types";
import type { AuditEntry } from "@/components/AuditTimeline";
import {
  useProjectDocumentScores,
  useProjectFeedbackData,
  useProjectFSVStatus,
  useProjectReviewCycleData,
  useProjectVersionHistory,
} from "@/lib/projectPageDataHooks";

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

export interface ReviewAssignment {
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
  /** "inline" for TipTap-extracted marks, undefined for manual entries */
  source?: string | null;
  /** Position range anchor "from:to" for inline feedback */
  range_anchor?: string | null;
}

export interface FeedbackProgress {
  total: number;
  open: number;
  accepted: number;
  rejected: number;
  resolved: number;
  addressed: number;
  by_type: Record<string, number>;
}

export interface NotifLogEntry {
  id: string;
  event: string;
  message: string;
  reviewer?: string | null;
  sent_at: string;
  channel: string;
}

export interface ReviewSummary {
  total_active: number;
  invited: number;
  reviewing: number;
  feedback_submitted: number;
  concurred: number;
  non_concurred: number;
  signed: number;
  declined: number;
  all_complete: boolean;
  all_signed: boolean;
  has_non_concurrence: boolean;
  lifecycle_step: string;
  feedback_total: number;
  feedback_open: number;
  feedback_addressed: number;
}

export interface LifecycleRecord {
  project_id: string;
  status: string;
  updated_at: string;
  set_by?: string | null;
  published_ref?: string | null;
  published_at?: string | null;
  published_venue?: string | null;
}

export interface SLASummary {
  project_id: string;
  total: number;
  on_track: number;
  due_soon: number;
  overdue: number;
  no_deadline: number;
  max_overdue_days: number;
}

export interface DeadlineStatus {
  assignment_id: string;
  reviewer: string;
  due_date?: string | null;
  days_remaining?: number | null;
  status: string;
  overdue_days: number;
}

export interface EligibilityResult {
  eligible: boolean;
  open_items: number;
  unanswered_questions: number;
  total_feedback: number;
  reason?: string | null;
}

export interface DocumentScore {
  document_id: string;
  quality_score: number;
  plain_language_grade: string;
  flesch_reading_ease: number;
  quality_flags: Record<string, number>;
  high_risk_terms: string[];
  doc_type_avg_score: number | null;
}

export interface UserDirectoryEntry {
  username?: string | null;
}

// ---------------------------------------------------------------------------
// PROJECT_LIFECYCLE_STATUSES — kept here for use by hook + components
// ---------------------------------------------------------------------------
export const PROJECT_LIFECYCLE_STATUSES = [
  "draft",
  "in_review",
  "reviewed",
  "ready_for_publication",
  "published",
  "submitted_to_records",
  "closed",
] as const;

export type ProjectLifecycleStatus = (typeof PROJECT_LIFECYCLE_STATUSES)[number];

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseProjectPageDataInput {
  username: string | undefined;
  approvals: Approval[];
  approvalsForPhase: Approval[];
  project: Project | null;
  workflow: Workflow | null;
  reviewCountData: { count?: number } | null | undefined;
  logs: LogEntry[];
}

export function useProjectPageData(
  id: string | undefined,
  {
    username,
    approvals: _approvals,
    approvalsForPhase,
    project: _project,
    workflow: _workflow,
    reviewCountData: _reviewCountData,
    logs,
  }: UseProjectPageDataInput,
) {
  // -------------------------------------------------------------------------
  // User directory
  // -------------------------------------------------------------------------
  const {
    userOptionsQuery,
    assignmentsQuery,
    reviewSummaryQuery,
    myAssignmentsQuery,
    lifecycleQuery,
  } = useProjectReviewCycleData(id);
  const { feedbackItemsQuery, feedbackProgressQuery, notifLogQuery } = useProjectFeedbackData(id);
  const qualityScoresQuery = useProjectDocumentScores(id);
  const versionsQuery = useProjectVersionHistory(id);
  const fsvEnabledQuery = useProjectFSVStatus();

  const { data: userOptions = [] } = userOptionsQuery;
  const { data: assignments = [], refetch: refetchAssignments } = assignmentsQuery;
  const { data: reviewSummary, refetch: refetchSummary } = reviewSummaryQuery;
  const { data: myAssignments = [], refetch: refetchMyAssignments } = myAssignmentsQuery;
  const { data: lifecycleRecord, refetch: refetchLifecycle } = lifecycleQuery;
  const { data: feedbackItems = [], refetch: refetchFeedback } = feedbackItemsQuery;
  const { data: feedbackProgress, refetch: refetchProgress } = feedbackProgressQuery;
  const { data: notifLog = [] } = notifLogQuery;

  // -------------------------------------------------------------------------
  // SLA summary
  // -------------------------------------------------------------------------
  const { data: slaSummary, refetch: refetchSla } = useQuery<SLASummary>({
    queryKey: ["sla-summary", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await authenticatedFetch(`/projects/${id}/sla-summary`);
      return res.ok ? res.json() : null;
    },
    enabled: !!id,
    staleTime: 60_000,
  });

  const { data: slaDeadlines = [] } = useQuery<DeadlineStatus[]>({
    queryKey: ["sla-deadlines", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/sla-deadlines`);
      return res.ok ? res.json() : [];
    },
    enabled: !!id,
    staleTime: 60_000,
  });

  // -------------------------------------------------------------------------
  // Document quality scores
  // -------------------------------------------------------------------------
  const { data: qualityScores } = qualityScoresQuery;
  const { data: fsvEnabled = true } = fsvEnabledQuery;
  const { data: versions = [] } = versionsQuery;

  // -------------------------------------------------------------------------
  // Assignment eligibility cache
  // -------------------------------------------------------------------------
  const [eligibilityCache, setEligibilityCache] = React.useState<
    Record<string, EligibilityResult | undefined>
  >({});

  // Auto-start invited assignments when reviewer opens project view
  useEffect(() => {
    if (!id || !username) return;
    authenticatedFetch(`/projects/${id}/assignments/view`, { method: "POST" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.started?.length > 0) {
          refetchAssignments();
          refetchMyAssignments();
          refetchSummary();
        }
      })
      .catch((err: unknown) => { console.warn("[view-tracking] failed:", err); }); // best-effort
  }, [id, username, refetchAssignments, refetchMyAssignments, refetchSummary]);

  // Fetch eligibility for each active assignment
  useEffect(() => {
    if (!id || assignments.length === 0) return;
    let cancelled = false;
    const active = assignments.filter(
      (a) => !["replaced", "concurred", "signed", "declined"].includes(a.status),
    );
    Promise.all(
      active.map(async (a) => {
        const res = await authenticatedFetch(
          `/projects/${id}/assignments/${a.id}/eligibility`,
        ).catch(() => null);
        if (res?.ok) {
          const data: EligibilityResult = await res.json();
          return [a.id, data] as const;
        }
        return null;
      }),
    ).then((results) => {
      if (cancelled) return;
      const cache: Record<string, EligibilityResult | undefined> = {};
      for (const r of results) {
        if (r) cache[r[0]] = r[1];
      }
      setEligibilityCache(cache);
    });
    return () => {
      cancelled = true;
    };
  }, [id, assignments, setEligibilityCache]);

  // -------------------------------------------------------------------------
  // Derived memos
  // -------------------------------------------------------------------------

  const assignmentReviewers = useMemo(
    () =>
      Array.from(
        new Set(
          assignments.filter((a) => a.status !== "replaced").map((a) => a.reviewer),
        ),
      ),
    [assignments],
  );

  const allUsernames = useMemo<string[]>(
    () =>
      Array.from(
        new Set(
          userOptions.flatMap((user) => {
            const uname =
              typeof user?.username === "string" ? user.username.trim() : "";
            return uname ? [uname] : [];
          }),
        ),
      ).sort((l, r) => l.localeCompare(r)),
    [userOptions],
  );

  const reviewerUsernames = useMemo<string[]>(
    () =>
      approvalsForPhase
        .map((a) => a.reviewer)
        .filter((r): r is string => typeof r === "string" && r.trim().length > 0),
    [approvalsForPhase],
  );

  const approvalReviewerOptions = useMemo<string[]>(
    () =>
      Array.from(
        new Set<string>([...allUsernames, ...assignmentReviewers, ...reviewerUsernames]),
      ).sort((l, r) => l.localeCompare(r)),
    [allUsernames, assignmentReviewers, reviewerUsernames],
  );

  const requiredApprovalsForPhase = useMemo(
    () => approvalsForPhase.filter((a) => a.required !== false),
    [approvalsForPhase],
  );

  const completedApprovalCount = useMemo(
    () =>
      requiredApprovalsForPhase.filter((a) => a.state === "approved").length,
    [requiredApprovalsForPhase],
  );

  const activeAssignments = useMemo(
    () => assignments.filter((a) => a.status !== "replaced"),
    [assignments],
  );

  const completedAssignmentsCount = useMemo(
    () =>
      activeAssignments.filter((a) =>
        ["concurred", "signed", "non_concurred", "declined"].includes(a.status),
      ).length,
    [activeAssignments],
  );

  const displayLifecycleStatus = useMemo(() => {
    const persistedStatus = lifecycleRecord?.status ?? "draft";
    const persistedIndex = PROJECT_LIFECYCLE_STATUSES.indexOf(
      persistedStatus as ProjectLifecycleStatus,
    );
    let derivedIndex = persistedIndex >= 0 ? persistedIndex : 0;

    if (activeAssignments.length > 0) {
      derivedIndex = Math.max(
        derivedIndex,
        PROJECT_LIFECYCLE_STATUSES.indexOf("in_review"),
      );
    }
    if (reviewSummary?.all_complete) {
      derivedIndex = Math.max(
        derivedIndex,
        PROJECT_LIFECYCLE_STATUSES.indexOf("reviewed"),
      );
    }

    return PROJECT_LIFECYCLE_STATUSES[derivedIndex] ?? persistedStatus;
  }, [activeAssignments.length, lifecycleRecord?.status, reviewSummary?.all_complete]);

  const lifecycleReviewHint = useMemo(() => {
    if (!reviewSummary || !lifecycleRecord) return null;
    if (
      lifecycleRecord.status === "draft" &&
      displayLifecycleStatus === "in_review"
    ) {
      return "Review activity has started, but the formal project lifecycle has not been advanced yet.";
    }
    if (
      lifecycleRecord.status !== "reviewed" &&
      displayLifecycleStatus === "reviewed"
    ) {
      return "Reviewer sign-off is complete. Advance the formal project lifecycle when you are ready.";
    }
    return null;
  }, [displayLifecycleStatus, lifecycleRecord, reviewSummary]);

  const assignmentEvents = useMemo<AuditEntry[]>(() => {
    const events: AuditEntry[] = [];
    for (const a of assignments) {
      if (a.requested_at) {
        events.push({
          id: `${a.id}-invited`,
          timestamp: a.requested_at,
          message: `Reviewer '${a.reviewer}' invited`,
          type: "review" as const,
        });
      }
      if (a.started_at) {
        events.push({
          id: `${a.id}-started`,
          timestamp: a.started_at,
          message: `Reviewer '${a.reviewer}' started review`,
          type: "review" as const,
        });
      }
      if (a.completed_at) {
        events.push({
          id: `${a.id}-submitted`,
          timestamp: a.completed_at,
          message: `Reviewer '${a.reviewer}' submitted feedback`,
          type: "review" as const,
        });
      }
      if (a.signed_at) {
        events.push({
          id: `${a.id}-signed`,
          timestamp: a.signed_at,
          message: `Reviewer '${a.reviewer}' ${
            a.status === "non_concurred"
              ? "non-concurred"
              : a.status === "signed"
              ? "signed (internal)"
              : "concurred"
          }`,
          type: "review" as const,
        });
      }
    }
    return events;
  }, [assignments]);

  const auditEvents = useMemo(() => {
    const base = logs.map((l) => ({
      id: l.id,
      timestamp: l.timestamp,
      message: l.action,
      type: l.type,
      link:
        l.type === "approval" && l.ref
          ? `#approval-${l.ref}`
          : l.type === "review" && l.ref
          ? `/projects/${id}/reviews#${l.ref}`
          : undefined,
    }));
    return [...base, ...assignmentEvents].sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    );
  }, [logs, id, assignmentEvents]);

  const reviewerOptions = useMemo(
    () =>
      userOptions
        .filter(
          (u: UserDirectoryEntry & { roles?: string[] }) =>
            Array.isArray((u as any).roles) && (u as any).roles.includes("reviewer"),
        )
        .map((u: UserDirectoryEntry & { username?: string | null }) => u.username as string),
    [userOptions],
  );

  return {
    // queries
    userOptions,
    versions,
    assignments,
    refetchAssignments,
    feedbackItems,
    refetchFeedback,
    feedbackProgress,
    refetchProgress,
    notifLog,
    reviewSummary,
    refetchSummary,
    myAssignments,
    refetchMyAssignments,
    lifecycleRecord,
    refetchLifecycle,
    slaSummary,
    refetchSla,
    slaDeadlines,
    qualityScores,
    fsvEnabled,
    // eligibility
    eligibilityCache,
    // derived
    assignmentReviewers,
    allUsernames,
    reviewerUsernames,
    approvalReviewerOptions,
    requiredApprovalsForPhase,
    completedApprovalCount,
    activeAssignments,
    completedAssignmentsCount,
    displayLifecycleStatus,
    lifecycleReviewHint,
    assignmentEvents,
    auditEvents,
    reviewerOptions,
  };
}
