// frontend/pages/projects/[id]/index.tsx
"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { authenticatedFetch } from "@/lib/api";
import { ApprovalTable, AuditTimeline, ProjectSummaryBar, KpiCards, PhaseAdvanceModal, WorkflowTimeline, ReviewerComments, UserPicker, HelpTooltip } from "@/components";
import type { TimelineStep } from "@/components";
import type { AuditEntry } from "@/components/AuditTimeline";
import { cn } from "@/lib/utils";
import { useProject } from "@/lib/useProject";
import { usePhases } from "@/lib/usePhases";
import { useApprovals } from "@/lib/useApprovals";
import { useProjectReviewers } from "@/lib/useProjectReviewers";
import { useReviewSummary } from "@/lib/useReviewSummary";
import { useUserStore } from "@/state/user";
import { Disclosure, Transition } from "@headlessui/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
    FileEdit,
    History,
    LayoutList,
    Download,
    Mail,
    Users2,
    UserPlus,
    Pencil,
    Trash2,
    CheckCircle2,
    XCircle,
    Clock,
    MessageSquare,
    HelpCircle,
    Lightbulb,
    AlertTriangle,
    ChevronDown,
    ChevronRight,
    Bell,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/router";
import React, {
    Fragment,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";
import { toast } from "react-hot-toast";

// Sub-components extracted from this file (R-09)
import {
  type Project,
  type LogEntry,
  type WorkflowStep,
  type Workflow,
  type Approval,
  type VersionEntry,
  ProgBar,
  LifecycleStepper,
  LIFECYCLE_STEPS,
  StickyNav,
  NAV,
  VersionDrawer,
} from "@/components/project";

// ---------------------------------------------------------------------------
// 1 ▲ Utility helpers (types moved to @/components/project/_types)
// ---------------------------------------------------------------------------
const slug = (s: string) => s.toLowerCase().replace(/\s+/g, "");
function classNames(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

const PHASE_CHECKS: Record<string, string[]> = {
  draft: ["Draft completed"],
  review: ["Review feedback addressed"],
  approval: ["Approval package prepared"],
};

// ----------------------------------------------------------------------------
// 4 ▲ Main component
// ----------------------------------------------------------------------------
export default function ProjectDetailsPage() {
  const router = useRouter();
  // Guard against undefined id during Next.js router hydration. On the first
  // render router.query is empty ({}); wait until router.isReady before using it.
  const id = router.isReady ? (router.query.id as string | undefined) : undefined;

  // ▼ state
  const [project, setProject] = useState<Project | null>(null);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [historyEvents, setHistoryEvents] = useState<AuditEntry[]>([]);
  const [versions] = useState<VersionEntry[]>([]);
  const [reviewCount, setReviewCount] = useState(0);
  const [showPhaseDialog, setShowPhaseDialog] = useState(false);
  const [pendingPhase, setPendingPhase] = useState<string | null>(null);
  const [reviewerInput, setReviewerInput] = useState("");
  const [reviewerActionError, setReviewerActionError] = useState<string | null>(null);
  const [addingReviewer, setAddingReviewer] = useState(false);
  const [approvalReviewerInput, setApprovalReviewerInput] = useState("");
  const [approvalActionError, setApprovalActionError] = useState<string | null>(null);
  const [addingApproval, setAddingApproval] = useState(false);
  const [editingReviewer, setEditingReviewer] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");

  // Assignment-based reviewer state
  const [assignmentReviewerInput, setAssignmentReviewerInput] = useState("");
  const [assignmentDueDate, setAssignmentDueDate] = useState("");
  const [addingAssignment, setAddingAssignment] = useState(false);
  const [expandedFeedback, setExpandedFeedback] = useState<Set<string>>(new Set());
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [feedbackTypeFilter, setFeedbackTypeFilter] = useState("all");
  const [feedbackStatusFilter, setFeedbackStatusFilter] = useState("all");
  const [newFeedbackText, setNewFeedbackText] = useState("");
  const [newFeedbackType, setNewFeedbackType] = useState("comment");

  const approvalsForPhase = useMemo(
    () =>
      approvals.filter(
        (a) => !project?.currentPhaseId || a.phaseId === project.currentPhaseId,
      ),
    [approvals, project?.currentPhaseId],
  );

  const [showVersions, setShowVersions] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  // NARA records retention fields (Phase 7)
  const [naraScheduleNumber, setNaraScheduleNumber] = useState("");
  const [naraDispositionAuthority, setNaraDispositionAuthority] = useState("");
  const [naraRetentionPeriod, setNaraRetentionPeriod] = useState("");
  const [naraRecordSeries, setNaraRecordSeries] = useState("");
  const [savingNara, setSavingNara] = useState(false);

  // Reviewer-centric feedback filter (Phase 5) — must be declared here (before any early returns)
  const [feedbackShowMyOnly, setFeedbackShowMyOnly] = React.useState(false);

  // ▼ permission based on logged in user
  const username = useUserStore((s) => s.username);
  const isAdmin = useUserStore((s) => s.isAdmin);
  const isOwner = project?.owner === username;
  const canEdit = isOwner || isAdmin;

  const phaseList = useMemo(
    () => workflow?.steps?.map((s) => ({ id: s.name, name: s.name })) ?? [],
    [workflow?.steps],
  );

  const phaseCounts = useMemo(() => {
    const map: Record<string, number> = {};
    approvals.forEach((a) => {
      if (a.phaseId) map[a.phaseId] = (map[a.phaseId] || 0) + 1;
    });
    return map;
  }, [approvals]);

  const canAdvance = useMemo(
    () =>
      approvalsForPhase.length === 0 ||
      approvalsForPhase
        .filter((a) => a.required !== false)
        .every((a) => a.state === "approved"),
    [approvalsForPhase],
  );

  const timelineSteps = useMemo<TimelineStep[]>(
    () =>
      workflow?.steps?.map((s) => ({
        name: s.name,
        status: (s.status ?? "upcoming") as TimelineStep["status"],
      })) ?? [],
    [workflow?.steps],
  );

  // ▼ data hooks
  const { data: projectData, isLoading: projectLoading, isError: projectError } = useProject(id as string);
  const { data: workflowData, isLoading: phasesLoading } = usePhases(projectData?.workflow);
  const {
    approvals: approvalsData,
    approve,
    reset,
    remind,
    isLoading: approvalsLoading,
  } = useApprovals({ workflow: projectData?.workflow });
  const { data: reviewCountData, isLoading: reviewLoading } = useReviewSummary(
    projectData?.id,
    projectData?.currentPhaseId ?? undefined,
  );
  const queryClient = useQueryClient();
  const {
    reviewers,
    addReviewer,
    updateReviewer,
    removeReviewer,
    isLoading: reviewersLoading,
  } = useProjectReviewers(projectData?.id);
  const { data: userOptions = [] } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await authenticatedFetch('/users');
      if (!res.ok) return [];
      return res.json();
    },
  });

  // Reviewer assignments (lifecycle model)
  interface ReviewAssignment {
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
  const { data: assignments = [], refetch: refetchAssignments } = useQuery<ReviewAssignment[]>({
    queryKey: ["assignments", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/assignments`);
      return res.ok ? res.json() : [];
    },
    enabled: !!id,
    staleTime: 30_000,
  });
  const assignmentReviewers = useMemo(
    () => Array.from(new Set(assignments.filter((a) => a.status !== "replaced").map((a) => a.reviewer))),
    [assignments],
  );
  const approvalReviewerOptions = useMemo(
    () => Array.from(new Set([...assignmentReviewers, ...reviewers])).sort((left, right) => left.localeCompare(right)),
    [assignmentReviewers, reviewers],
  );

  // Feedback ledger
  interface FeedbackItem {
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
  interface FeedbackProgress {
    total: number;
    open: number;
    accepted: number;
    rejected: number;
    resolved: number;
    addressed: number;
    by_type: Record<string, number>;
  }
  const { data: feedbackItems = [], refetch: refetchFeedback } = useQuery<FeedbackItem[]>({
    queryKey: ["feedback", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/feedback`);
      if (!res.ok) return [];
      const data = await res.json();
      // The endpoint returns either a plain array or a paginated envelope
      // { items: [...], total, skip, limit }. Normalise both.
      if (Array.isArray(data)) return data as FeedbackItem[];
      if (data && Array.isArray(data.items)) return data.items as FeedbackItem[];
      return [];
    },
    enabled: !!id,
    staleTime: 15_000,
  });
  const { data: feedbackProgress, refetch: refetchProgress } = useQuery<FeedbackProgress>({
    queryKey: ["feedback-progress", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await authenticatedFetch(`/projects/${id}/feedback/progress`);
      return res.ok ? res.json() : null;
    },
    enabled: !!id,
    staleTime: 15_000,
  });

  // Notification log
  interface NotifLogEntry {
    id: string;
    event: string;
    message: string;
    reviewer?: string | null;
    sent_at: string;
    channel: string;
  }
  const { data: notifLog = [] } = useQuery<NotifLogEntry[]>({
    queryKey: ["notif-log", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/notification-log`);
      return res.ok ? res.json() : [];
    },
    enabled: !!id,
    staleTime: 60_000,
  });

  // Review lifecycle summary (Phase 6)
  interface ReviewSummary {
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
  const { data: reviewSummary, refetch: refetchSummary } = useQuery<ReviewSummary>({
    queryKey: ["review-summary", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await authenticatedFetch(`/projects/${id}/review-summary`);
      return res.ok ? res.json() : null;
    },
    enabled: !!id,
    staleTime: 15_000,
  });

  // My assignments on this project (Phase 5)
  const { data: myAssignments = [], refetch: refetchMyAssignments } = useQuery<ReviewAssignment[]>({
    queryKey: ["my-assignments", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/assignments/me`);
      return res.ok ? res.json() : [];
    },
    enabled: !!id,
    staleTime: 30_000,
  });

  // Lifecycle status (Phase 7)
  interface LifecycleRecord {
    project_id: string;
    status: string;
    updated_at: string;
    set_by?: string | null;
    published_ref?: string | null;
    published_at?: string | null;
    published_venue?: string | null;
  }
  const { data: lifecycleRecord, refetch: refetchLifecycle } = useQuery<LifecycleRecord>({
    queryKey: ["lifecycle", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await authenticatedFetch(`/projects/${id}/lifecycle`);
      return res.ok ? res.json() : { project_id: id, status: "draft", updated_at: "" };
    },
    enabled: !!id,
    staleTime: 30_000,
  });

  // SLA summary (Phase 8)
  interface SLASummary {
    project_id: string;
    total: number;
    on_track: number;
    due_soon: number;
    overdue: number;
    no_deadline: number;
    max_overdue_days: number;
  }
  interface DeadlineStatus {
    assignment_id: string;
    reviewer: string;
    due_date?: string | null;
    days_remaining?: number | null;
    status: string;
    overdue_days: number;
  }
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

  // Assignment eligibility cache — stores full eligibility objects
  interface EligibilityResult {
    eligible: boolean;
    open_items: number;
    unanswered_questions: number;
    total_feedback: number;
    reason?: string | null;
  }
  const [eligibilityCache, setEligibilityCache] = React.useState<Record<string, EligibilityResult | undefined>>({});

  // Auto-start invited assignments when reviewer opens project view (Phase 5)
  useEffect(() => {
    if (!id || !username) return;
    authenticatedFetch(`/projects/${id}/assignments/view`, { method: "POST" })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.started?.length > 0) {
          refetchAssignments();
          refetchMyAssignments();
          refetchSummary();
        }
      })
      .catch(() => {}); // best-effort
  }, [id, username, refetchAssignments, refetchMyAssignments, refetchSummary]);

  // Fetch eligibility for each active assignment
  useEffect(() => {
    if (!id || assignments.length === 0) return;
    let cancelled = false;
    const active = assignments.filter((a) => !["replaced", "concurred", "signed", "declined"].includes(a.status));
    Promise.all(
      active.map(async (a) => {
        const res = await authenticatedFetch(
          `/projects/${id}/assignments/${a.id}/eligibility`
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
    return () => { cancelled = true; };
  }, [id, assignments, setEligibilityCache]);

  const reviewerOptions = useMemo(
    () =>
      userOptions
        .filter((u: any) => Array.isArray(u.roles) && u.roles.includes("reviewer"))
        .map((u: any) => u.username),
    [userOptions],
  );

  useEffect(() => {
    setProject(projectData ?? null);
    if (projectData) {
      setNaraScheduleNumber(projectData.nara_schedule_number ?? "");
      setNaraDispositionAuthority(projectData.nara_disposition_authority ?? "");
      setNaraRetentionPeriod(projectData.nara_retention_period ?? "");
      setNaraRecordSeries(projectData.nara_record_series ?? "");
    }
  }, [projectData, id]);
  useEffect(() => {
    setWorkflow(workflowData ?? null);
  }, [workflowData, id]);
  useEffect(() => {
    setApprovals(approvalsData ?? []);
  }, [approvalsData, id]);
  useEffect(() => {
    setReviewCount(reviewCountData?.count ?? 0);
  }, [reviewCountData, id]);

  useEffect(() => {
    if (!id || !username) {
      setLogs([]);
      return;
    }
    authenticatedFetch(`/api/audit?entity_id=${id}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setLogs(
          data.map((d) => ({
            id: d.id ?? d.timestamp,
            timestamp: d.timestamp,
            action: d.details?.message || d.action,
            type: (d.details?.type as LogEntry["type"]) || "edit",
            ref:
              d.details?.approvalId ||
              d.details?.reviewId ||
              d.details?.phaseId,
          })),
        ),
      )
      .catch(() => setLogs([]));
  }, [id, username]);

  const loading = projectLoading || phasesLoading || approvalsLoading || reviewLoading;

  // Synthetic review lifecycle events derived from assignment timestamps
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
          message: `Reviewer '${a.reviewer}' ${a.status === "non_concurred" ? "non-concurred" : a.status === "signed" ? "signed (internal)" : "concurred"}`,
          type: "review" as const,
        });
      }
    }
    return events;
  }, [assignments]);

  const auditEvents = useMemo(
    () => {
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
      // Merge and sort by timestamp descending
      return [...base, ...assignmentEvents].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      );
    },
    [logs, id, assignmentEvents],
  );

  // ▼ check for completed signatures on page load
  useEffect(() => {
    if (!approvals.length) return;

    // Check localStorage for completed signatures
    approvals.forEach((approval) => {
      if (approval.documensoSigId) {
        const completedAt = localStorage.getItem(`approval-${approval.id}`);
        if (completedAt && approval.state !== "approved") {
          // Update the approval state to reflect completion
          setApprovals((prev) =>
            prev.map((a) =>
              a.id === approval.id
                ? {
                    ...a,
                    state: "approved" as const,
                    signedAt: completedAt,
                    documensoSigId: approval.documensoSigId
                  }
                : a,
            ),
          );

          // Sync with backend
          syncApprovalWithBackend(approval.id, approval.documensoSigId);
        }
      }
    });
  }, [approvals]);

  // ▼ review KPIs memo
  const stats = useMemo(() => {
    const assigned = approvalsForPhase.length;
    return {
      assigned,
      approved: approvalsForPhase.filter((a) => a.state === "approved").length,
      pending: approvalsForPhase.filter((a) => a.state === "pending").length,
      overdue: approvalsForPhase.filter((a) => a.state === "overdue").length,
    };
  }, [approvalsForPhase]);

  // ▼ document quality scores
  interface DocumentScore {
    document_id: string;
    quality_score: number;
    plain_language_grade: string;
    flesch_reading_ease: number;
    quality_flags: Record<string, number>;
    high_risk_terms: string[];
    doc_type_avg_score: number | null;
  }
  const { data: qualityScores } = useQuery<DocumentScore[]>({
    queryKey: ["project-doc-scores", id],
    queryFn: async () => {
      const res = await authenticatedFetch(`/projects/${id}/documents/scores`);
      if (!res.ok) return [];
      return res.json();
    },
    enabled: !!id,
    staleTime: 60_000,
  });

  // Item 34 Phase 4: gate FSV-specific UI on FSV plugin enabled state
  const { data: fsvEnabled = true } = useQuery<boolean>({
    queryKey: ["fsv-enabled"],
    queryFn: async () => {
      const res = await authenticatedFetch("/plugin-marketplace/builtin-status");
      if (!res.ok) return true;
      const status: Record<string, boolean> = await res.json();
      return status["fedstylevalidator"] !== false;
    },
    staleTime: 60_000,
  });

  // ▼ handlers --------------------------------------------------------------
  const handlePhaseChange = useCallback(
    (phaseId: string) => {
      if (!workflow?.steps) return;
      const idx = workflow.steps.findIndex((s) => s.name === phaseId);
      if (idx === -1) return;
      const steps = workflow.steps.map((s, i) => ({
        ...s,
        status:
          i < idx
            ? ("complete" as const)
            : i === idx
              ? ("active" as const)
              : ("pending" as const),
      }));
      setWorkflow({ ...workflow, steps, phase: steps[idx].name });
      setProject((prev) =>
        prev ? { ...prev, currentPhaseId: steps[idx].name } : prev,
      );
    },
    [workflow],
  );

  const requestPhaseChange = useCallback(
    (phaseId: string) => {
      if (phaseId === project?.currentPhaseId) return;
      if (!canAdvance) {
        toast.error("All required approvals must be complete before advancing the phase.");
        return;
      }
      setPendingPhase(phaseId);
      setShowPhaseDialog(true);
    },
    [project?.currentPhaseId, canAdvance],
  );

  const confirmPhaseChange = useCallback(async () => {
    if (pendingPhase && project?.id) {
      try {
        const res = await authenticatedFetch(`/projects/${project.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phase: pendingPhase }),
        });
        if (!res.ok) {
          throw new Error("Failed to update project phase");
        }
        handlePhaseChange(pendingPhase);
        queryClient.invalidateQueries({ queryKey: ["project", project.id] });
        if (project.workflow) {
          queryClient.invalidateQueries({ queryKey: ["workflow", project.workflow] });
        }
      } catch (error) {
        console.error(error);
        toast.error("Failed to update phase");
      }
    }
    setShowPhaseDialog(false);
    setPendingPhase(null);
  }, [pendingPhase, project, handlePhaseChange, queryClient]);

  const refreshReviewerData = useCallback(() => {
    if (!project?.id) return;
    queryClient.invalidateQueries({ queryKey: ["project", project.id] });
    queryClient.invalidateQueries({ queryKey: ["project-reviewers", project.id] });
    if (project.workflow) {
      queryClient.invalidateQueries({ queryKey: ["approvals", project.workflow] });
      queryClient.invalidateQueries({ queryKey: ["workflow", project.workflow] });
    }
  }, [project?.id, project?.workflow, queryClient]);

  const createApprovalForReviewer = useCallback(
    async (reviewer: string) => {
      if (!project?.workflow) {
        throw new Error("This project has no workflow configured.");
      }

      const phaseId = project.currentPhaseId ?? workflow?.phase ?? undefined;
      const alreadyExists = approvals.some(
        (a) =>
          a.reviewer === reviewer &&
          ((phaseId && a.phaseId === phaseId) || (!phaseId && !a.phaseId)),
      );

      if (alreadyExists) {
        return false;
      }

      const response = await authenticatedFetch('/approvals', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow: project.workflow,
          reviewer,
          phase_id: phaseId,
          required: true,
          description: "Review Approval",
        }),
      });

      if (!response.ok) {
        let detail = "Failed to create approval";
        try {
          const data = await response.json();
          if (typeof data?.detail === "string" && data.detail.trim()) {
            detail = data.detail;
          }
        } catch {
          // ignore parse failure and keep default message
        }
        throw new Error(detail);
      }

      const created = await response.json();
      setApprovals((prev) => [
        {
          id: created.id,
          reviewer: created.reviewer,
          email: created.reviewer,
          state: created.state,
          dueAt: created.due_at || new Date().toISOString().split("T")[0],
          signedAt: created.signed_at,
          comments: created.comments || "",
          documensoSigId: created.signature || created.signature_id,
          description: created.description,
          phaseId: created.phase_id,
          required: created.required,
        },
        ...prev,
      ]);

      refreshReviewerData();
      return true;
    },
    [approvals, project?.currentPhaseId, project?.workflow, refreshReviewerData, workflow?.phase],
  );
  const handleAddReviewer = useCallback(async () => {
    const reviewer = reviewerInput.trim();
    if (!reviewer) {
      const message = "Select a reviewer to add.";
      setReviewerActionError(message);
      toast.error(message);
      return;
    }
    if (reviewerOptions.length > 0 && !reviewerOptions.includes(reviewer)) {
      const message = "Reviewer must be an existing reviewer username.";
      setReviewerActionError(message);
      toast.error(message);
      return;
    }
    try {
      setAddingReviewer(true);
      setReviewerActionError(null);
      await addReviewer(reviewer);
      const created = await createApprovalForReviewer(reviewer);
      setReviewerInput("");
      if (!created) {
        toast("Reviewer added. Approval already exists for this phase.");
      }
      refreshReviewerData();
    } catch (error) {
      console.error(error);
      const message = error instanceof Error ? error.message : "Failed to add reviewer";
      setReviewerActionError(message);
    } finally {
      setAddingReviewer(false);
    }
  }, [addReviewer, createApprovalForReviewer, reviewerInput, reviewerOptions, refreshReviewerData]);


  const handleAddApproval = useCallback(async () => {
    const reviewer = approvalReviewerInput.trim();
    if (!reviewer) {
      const message = "Select a reviewer for the approval.";
      setApprovalActionError(message);
      toast.error(message);
      return;
    }
    if (!approvalReviewerOptions.includes(reviewer)) {
      const message = "Invite the reviewer in the Reviewers section before adding a phase approval.";
      setApprovalActionError(message);
      toast.error(message);
      return;
    }
    try {
      setAddingApproval(true);
      setApprovalActionError(null);
      const created = await createApprovalForReviewer(reviewer);
      if (!created) {
        const message = "Approval already exists for this reviewer in the current phase.";
        setApprovalActionError(message);
        toast(message);
        return;
      }
      setApprovalReviewerInput("");
      toast.success("Approval added.");
    } catch (error) {
      console.error(error);
      const message = error instanceof Error ? error.message : "Failed to add approval";
      setApprovalActionError(message);
      toast.error(message);
    } finally {
      setAddingApproval(false);
    }
  }, [approvalReviewerInput, approvalReviewerOptions, createApprovalForReviewer]);

  const handleUpdateReviewer = useCallback(async () => {
    if (!editingReviewer) return;
    const reviewer = editingValue.trim();
    if (!reviewer) {
      toast.error("Reviewer name required.");
      return;
    }
    try {
      await updateReviewer({ reviewer: editingReviewer, nextReviewer: reviewer });
      setEditingReviewer(null);
      setEditingValue("");
      refreshReviewerData();
    } catch (error) {
      console.error(error);
    }
  }, [editingReviewer, editingValue, updateReviewer, refreshReviewerData]);

  const handleRemoveReviewer = useCallback(
    async (reviewer: string) => {
      try {
        await removeReviewer(reviewer);
        refreshReviewerData();
      } catch (error) {
        console.error(error);
      }
    },
    [removeReviewer, refreshReviewerData],
  );

  // Assignment management handlers
  const handleAddAssignment = async () => {
    const reviewer = assignmentReviewerInput.trim();
    if (!reviewer) {
      toast.error("Enter a reviewer username.");
      return;
    }
    try {
      setAddingAssignment(true);
      const body: Record<string, unknown> = { reviewer };
      if (assignmentDueDate) body.due_date = assignmentDueDate;
      const res = await authenticatedFetch(`/projects/${id}/assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail ?? "Failed to add reviewer");
      }
      setAssignmentReviewerInput("");
      setAssignmentDueDate("");
      refetchAssignments();
      toast.success("Reviewer invited.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add reviewer");
    } finally {
      setAddingAssignment(false);
    }
  };

  const handleSendReminder = async (assignmentId: string) => {
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/remind`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error("Failed");
      toast.success("Reminder sent.");
    } catch {
      toast.error("Failed to send reminder.");
    }
  };

  // Feedback handlers
  const handlePostFeedback = async () => {
    if (!newFeedbackText.trim()) return;
    try {
      const res = await authenticatedFetch(`/projects/${id}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: newFeedbackText, feedback_type: newFeedbackType }),
      });
      if (!res.ok) throw new Error("Failed");
      setNewFeedbackText("");
      refetchFeedback();
      refetchProgress();
      toast.success("Feedback submitted.");
    } catch {
      toast.error("Failed to submit feedback.");
    }
  };

  const handleDisposition = async (itemId: string, status: string, reason?: string) => {
    try {
      const body: Record<string, unknown> = { status };
      if (reason) body.reason = reason;
      const res = await authenticatedFetch(
        `/projects/${id}/feedback/${itemId}/disposition`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!res.ok) throw new Error("Failed");
      refetchFeedback();
      refetchProgress();
      toast.success(`Marked as ${status}.`);
    } catch {
      toast.error("Failed to update status.");
    }
  };

  const handleReply = async (parentId: string) => {
    const text = replyText[parentId]?.trim();
    if (!text) return;
    try {
      const res = await authenticatedFetch(`/projects/${id}/feedback/${parentId}/reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error("Failed");
      setReplyText((prev) => ({ ...prev, [parentId]: "" }));
      refetchFeedback();
      toast.success("Reply posted.");
    } catch {
      toast.error("Failed to post reply.");
    }
  };

  const sendReminder = (ids?: string[]) => {
    const targets = approvalsForPhase.filter(
      (a) =>
        (ids ? ids.includes(a.id) : true) &&
        (a.state === "pending" || a.state === "overdue"),
    );
    remind(targets.map((a) => a.id));
  };

  const viewHistory = useCallback((aid: string) => {
    authenticatedFetch(`/approvals/${aid}/history`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setHistoryEvents(
          data.map((d) => ({
            id: d.id ?? d.timestamp,
            timestamp: d.timestamp,
            message: d.event || d.action || d.message,
            type: "approval" as const,
          })),
        ),
      )
      .catch(() => setHistoryEvents([]))
      .finally(() => setShowHistory(true));
  }, []);

  const signApproval = async (aid: string) => {
    const existing = approvals.find((a) => a.id === aid);
    if (existing?.state === "approved") {
      toast.error("Approval already completed.");
      return;
    }
    if (existing?.reviewer !== username) {
      toast.error("You are not assigned to this approval.");
      return;
    }
    try {
      const data = await approve(aid);
      const sigId = data?.id ?? data?.signature?.id;
      const signatureUrl = data?.url;
      if (signatureUrl && typeof window !== "undefined") {
        if (signatureUrl.startsWith("/")) {
          router.push(signatureUrl);
        } else {
          try {
            const parsed = new URL(signatureUrl);
            if (parsed.origin === window.location.origin) {
              window.location.assign(parsed.href);
            }
          } catch {
            /* ignore invalid URLs */
          }
        }
        return;
      }
      if (sigId) {
        router.push(
          `/documenso/${encodeURIComponent(String(sigId))}?return=${encodeURIComponent(`/projects/${id}#approvals`)}&approval=${encodeURIComponent(aid)}`,
        );
      }
    } catch {
      /* handled in hook */
    }
  };

  const signApprovalByInitials = async (aid: string, initials: string) => {
    try {
      const res = await authenticatedFetch(`/approvals/${aid}/sign-initials`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initials }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to sign with initials");
        return;
      }
      const updated = await res.json();
      setApprovals((prev) => prev.map((a) => (a.id === aid ? { ...a, ...updated } : a)));
      toast.success("Approved with initials");
    } catch {
      toast.error("Failed to sign with initials");
    }
  };

  const resetApprovalLocal = async (aid: string) => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(`approval-${aid}`);
    }
    try {
      await reset(aid);
    } catch {
      /* handled in hook */
    }
  };

  const removeApproval = async (aid: string) => {
    try {
      const response = await authenticatedFetch(`/approvals/${aid}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to remove approval");
      }
      setApprovals((prev) => prev.filter((x) => x.id !== aid));
      toast.success("Approval removed");
    } catch (error) {
      console.error("Error removing approval:", error);
      toast.error("Failed to remove approval");
    }
  };

  const syncApprovalWithBackend = async (approvalId: string, signatureId: string) => {
    try {
      const response = await authenticatedFetch(`/approvals/${approvalId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          state: 'approved',
          signature: signatureId,
        }),
      });

      if (!response.ok) {
        console.error('Failed to sync approval with backend');
      }
    } catch (error) {
      console.error('Error syncing approval:', error);
    }
  };

  const exportRaci = () => {
    if (!project) return;
    const rows = [
      ["Task", "Accountable", "Responsible", "Consulted", "Informed"],
      [
        "Approval & signature",
        project.owner,
        approvalsForPhase.map((a) => a.reviewer).join(";"),
        "Writer",
        "Ops",
      ],
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `raci-${project.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadApprovalSummary = async () => {
    if (!project) return;
    try {
      const res = await authenticatedFetch(`/projects/${project.id}/approvals/pdf`);
      if (!res.ok) {
        toast.error("Failed to download summary");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `approvals-${project.id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      toast.error("Download failed");
    }
  };

  useEffect(() => {
    if (!isOwner) return;
    const overdue = approvalsForPhase.filter((a) => a.state === "overdue");
    if (overdue.length > 0) {
      toast.error(
        "Escalation: overdue approvals - " +
          overdue.map((o) => o.reviewer).join(", "),
      );
    }
  }, [approvalsForPhase, isOwner]);

  if (loading)
    return (
      <div className="p-4 space-y-4 animate-pulse">
        <div className="h-6 w-1/3 bg-gray-200 rounded" />
        <div className="h-4 w-full bg-gray-200 rounded" />
        <div className="h-4 w-5/6 bg-gray-200 rounded" />
      </div>
    );
  if (projectError)
    return (
      <div className="p-8 text-center space-y-3">
        <p className="text-red-600 font-medium">Unable to load project.</p>
        <p className="text-sm text-gray-500">
          The server could not be reached or returned an error. Check that the
          backend is running and your session is still active.
        </p>
        <button
          className="text-sm text-indigo-600 underline"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  if (!project) return <p className="p-4">Project not found.</p>;

  const editorURL = `/editors/${project.editor ?? "tiptap"}?projectId=${project.id}`;

  // ------------------------------------------------------------------------
  //                             RENDER
  // ------------------------------------------------------------------------

  // Sign-internal handler
  const handleSignInternal = async (assignmentId: string) => {
    const note = window.prompt("Optional note for internal acknowledgement:");
    if (note === null) return; // cancelled
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/sign-internal`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ note: note || null }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to sign");
        return;
      }
      toast.success("Internally acknowledged.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
    } catch {
      toast.error("Failed to sign.");
    }
  };

  // Concur handler (already exists in backend)
  const handleConcur = async (assignmentId: string) => {
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/concur`,
        { method: "POST" },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to concur");
        return;
      }
      toast.success("Concurred.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
    } catch {
      toast.error("Failed to concur.");
    }
  };

  // Submit review handler
  const handleSubmitReview = async (assignmentId: string) => {
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/submit`,
        { method: "POST" },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to submit review");
        return;
      }
      toast.success("Review submitted. The SME has been notified.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
    } catch {
      toast.error("Failed to submit review.");
    }
  };

  // Lifecycle transition handler (Phase 7)
  const handleLifecycleTransition = async (newStatus: string) => {
    if (!confirm(`Transition project status to "${newStatus.replace(/_/g, " ")}"?`)) return;
    try {
      const res = await authenticatedFetch(`/projects/${id}/lifecycle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to transition status");
        return;
      }
      refetchLifecycle();
      toast.success(`Project status → ${newStatus.replace(/_/g, " ")}`);
    } catch {
      toast.error("Failed to transition project status.");
    }
  };

  // Download records package (Phase 7)
  const handleDownloadRecordsPackage = async () => {
    try {
      const res = await authenticatedFetch(`/projects/${id}/records-package`);
      if (!res.ok) { toast.error("Failed to generate records package."); return; }
      const blob = await res.blob();
      const hash = res.headers.get("X-Content-Hash") ?? "";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `records-${id}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      if (hash) toast.success(`Downloaded. SHA-256: ${hash.replace("sha256=", "").slice(0, 16)}…`);
    } catch {
      toast.error("Download failed.");
    }
  };

  // Run SLA reminders manually (Phase 8)
  const handleRunSlaReminders = async () => {
    try {
      const res = await authenticatedFetch(`/projects/${id}/run-sla-reminders`, { method: "POST" });
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      toast.success(`${data.sent} reminder(s) sent.`);
      refetchSla();
    } catch {
      toast.error("Failed to send SLA reminders.");
    }
  };

  // Concur with comments handler
  const handleConcurWithComments = async (assignmentId: string) => {
    const text = window.prompt("Add your final comments for this concurrence (required):");
    if (!text?.trim()) return;
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/concur-with-comments`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to concur");
        return;
      }
      toast.success("Concurred with comments. Your notes have been added to the feedback ledger.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
      refetchFeedback();
    } catch {
      toast.error("Failed to concur.");
    }
  };

  // Request concurrence from a reviewer (SME action)
  const handleRequestConcurrence = async (assignmentId: string) => {
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/request-concurrence`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error("Failed");
      toast.success("Concurrence requested. Reviewer notified.");
    } catch {
      toast.error("Failed to request concurrence.");
    }
  };

  // Bulk remind all non-terminal reviewers
  const handleRemindAll = async () => {
    const targets = assignments.filter(
      (a) => !["replaced", "concurred", "signed", "declined"].includes(a.status),
    );
    if (targets.length === 0) {
      toast("No reviewers to remind.");
      return;
    }
    await Promise.all(targets.map((a) => handleSendReminder(a.id)));
    toast.success(`Reminder sent to ${targets.length} reviewer(s).`);
  };

  // Save NARA records retention metadata (Phase 7)
  const handleSaveNara = async () => {
    if (!id) return;
    setSavingNara(true);
    try {
      const res = await authenticatedFetch(`/projects/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nara_schedule_number: naraScheduleNumber || null,
          nara_disposition_authority: naraDispositionAuthority || null,
          nara_retention_period: naraRetentionPeriod || null,
          nara_record_series: naraRecordSeries || null,
        }),
      });
      if (!res.ok) throw new Error("Failed to save NARA metadata");
      toast.success("NARA metadata saved.");
      queryClient.invalidateQueries({ queryKey: ["project", id] });
    } catch {
      toast.error("Failed to save NARA metadata.");
    } finally {
      setSavingNara(false);
    }
  };

  // Export reviewer list as CSV
  const handleExportReviewers = () => {
    const rows = [
      ["Reviewer", "Status", "Invited", "Due Date", "Signed At"],
      ...assignments.map((a) => [
        a.reviewer,
        a.status,
        a.requested_at ? new Date(a.requested_at).toLocaleDateString() : "",
        a.due_date ? new Date(a.due_date).toLocaleDateString() : "",
        a.signed_at ? new Date(a.signed_at).toLocaleDateString() : "",
      ]),
    ];
    const csv = rows.map((r) => r.map((v) => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reviewers-${id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <StickyNav />
      <div className="p-8 space-y-10">

        {/* Lifecycle stepper — Phase 6 */}
        {reviewSummary && (
          <div className="rounded-xl border bg-white/60 dark:bg-gray-900/60 p-4 shadow-sm">
            <LifecycleStepper step={reviewSummary.lifecycle_step} />
          </div>
        )}

        {/* Reviewer focused banner — Phase 5 */}
        {myAssignments.filter((a) => !["replaced", "signed", "concurred", "declined"].includes(a.status)).map((ma) => (
          <div
            key={ma.id}
            className="rounded-xl border-2 border-indigo-300 bg-indigo-50 dark:bg-indigo-950 p-4 space-y-3"
          >
            <div className="flex items-start gap-3">
              <Users2 className="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-semibold text-indigo-800 dark:text-indigo-200">
                  You have been asked to review this project.
                </p>
                <p className="text-sm text-indigo-600 dark:text-indigo-400">
                  Status: <strong>{ma.status.replace(/_/g, " ")}</strong>
                  {ma.due_date && ` · Due: ${new Date(ma.due_date).toLocaleDateString()}`}
                </p>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button asChild size="sm">
                <Link href={`/editors/tiptap?projectId=${id}`}>
                  <FileEdit className="w-4 h-4 mr-1" /> Open Document
                </Link>
              </Button>
              {(() => {
                const elig = eligibilityCache[ma.id];
                const hasUnansweredQ = (elig?.unanswered_questions ?? 0) > 0;
                const hasOpenItems = (elig?.open_items ?? 0) > 0;
                const canSubmit = ma.status !== "feedback_submitted" && !hasUnansweredQ;
                const canConcur = elig?.eligible === true;
                return (
                  <>
                    {/* Waiting for SME Response — Phase 5 */}
                    {hasUnansweredQ && (
                      <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 self-center flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Waiting for SME Response — {elig!.unanswered_questions} question(s) unanswered
                      </span>
                    )}
                    {ma.status !== "feedback_submitted" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSubmitReview(ma.id)}
                        disabled={!canSubmit}
                        title={hasUnansweredQ ? "Cannot submit while questions are awaiting SME response" : undefined}
                      >
                        <CheckCircle2 className="w-4 h-4 mr-1" /> Submit Review
                      </Button>
                    )}
                    {canConcur && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-green-700 border-green-300"
                          onClick={() => handleConcur(ma.id)}
                        >
                          <CheckCircle2 className="w-4 h-4 mr-1" /> Concur
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-indigo-700 border-indigo-300"
                          onClick={() => handleConcurWithComments(ma.id)}
                        >
                          <MessageSquare className="w-4 h-4 mr-1" /> Concur with Comments
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-gray-600"
                          onClick={() => handleSignInternal(ma.id)}
                        >
                          Internal Sign-off
                        </Button>
                      </>
                    )}
                    {!canConcur && !hasUnansweredQ && hasOpenItems && (
                      <span className="text-xs text-amber-600 self-center">
                        <Clock className="w-3 h-3 inline mr-1" />
                        Concurrence gated — {elig!.open_items} open feedback item(s)
                      </span>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        ))}

        {/* All-reviews-complete banner — Phase 4 */}
        {reviewSummary?.all_complete && (
          <div className="rounded-xl border-2 border-green-400 bg-green-50 dark:bg-green-950 p-4 flex items-center gap-4 flex-wrap">
            <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-green-800 dark:text-green-200">
                All Reviews Complete — Ready for Next Phase
              </p>
              {reviewSummary.has_non_concurrence && (
                <p className="text-sm text-amber-600">
                  Note: one or more reviewers did not concur. Review their non-concurrence before advancing.
                </p>
              )}
            </div>
            {canEdit && (
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={() => setShowPhaseDialog(true)} className="bg-green-600 hover:bg-green-700">
                  Advance Phase
                </Button>
                <HelpTooltip
                  content="Advancing the phase moves the project to the next workflow stage. All reviewers must have submitted their feedback before you can advance. Non-concurrences should be addressed first."
                  href="/help#phases"
                />
              </div>
            )}
          </div>
        )}

        <ProjectSummaryBar
          project={{ ...project, currentPhaseId: project.currentPhaseId || workflow?.phase }}
          phases={phaseList}
          phaseCounts={phaseCounts}
          onPhaseChange={canEdit ? requestPhaseChange : undefined}
          onExportRaci={isOwner ? exportRaci : undefined}
          onShowVersions={() => setShowVersions(true)}
          isOwner={isOwner}
        />

        {/* OVERVIEW SECTION — Phase 6 */}
        <section id="overview" className="space-y-6">
          <Disclosure defaultOpen>
            {({ open }) => (
              <>
                <Disclosure.Button className="w-full text-left">
                  <h2 className="flex items-center gap-2 text-lg font-semibold">
                    <LayoutList className="w-5 h-5" /> Project Details{" "}
                    {open ? "" : "(collapsed)"}
                  </h2>
                </Disclosure.Button>
                <div className="text-right mt-2">
                  <Link
                    href={`/projects/${project.id}/edit`}
                    className="text-sm text-blue-600 underline"
                  >
                    Edit Project
                  </Link>
                </div>
                <Transition
                  show={open}
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <Card className="overflow-x-auto">
                    <CardContent>
                      <Table caption="Project details" className="min-w-[600px] text-sm">
                        <TableHeader>
                          <TableRow>
                            <TableHead>ID</TableHead>
                            <TableHead>#</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Title</TableHead>
                            <TableHead>Owner</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Updated</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          <TableRow>
                            <TableCell className="font-mono">
                              {project.id}
                            </TableCell>
                            <TableCell>{project.number}</TableCell>
                            <TableCell>{project.type}</TableCell>
                            <TableCell>{project.title}</TableCell>
                            <TableCell>{project.owner}</TableCell>
                            <TableCell>{project.status}</TableCell>
                            <TableCell>{project.updated}</TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </Transition>
              </>
            )}
          </Disclosure>

          <KpiCards stats={stats} />

          {/* Project Lifecycle Status — Phase 7 */}
          {lifecycleRecord && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                  Project Lifecycle
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-3 flex-wrap">
                  {["draft","in_review","reviewed","ready_for_publication","published","submitted_to_records","closed"].map((s) => {
                    const statuses = ["draft","in_review","reviewed","ready_for_publication","published","submitted_to_records","closed"];
                    const currentIdx = statuses.indexOf(lifecycleRecord.status);
                    const thisIdx = statuses.indexOf(s);
                    const done = thisIdx < currentIdx;
                    const active = thisIdx === currentIdx;
                    return (
                      <span
                        key={s}
                        className={cn(
                          "px-2 py-0.5 rounded text-xs font-medium",
                          done ? "bg-green-100 text-green-700" :
                          active ? "bg-indigo-100 text-indigo-700 ring-1 ring-indigo-400" :
                          "bg-gray-100 text-gray-400",
                        )}
                      >
                        {s.replace(/_/g, " ")}
                      </span>
                    );
                  })}
                </div>
                {/* Lifecycle transition buttons for SME/admin */}
                {canEdit && (() => {
                  const nextMap: Record<string, string[]> = {
                    draft: ["in_review"],
                    in_review: ["reviewed", "draft"],
                    reviewed: ["ready_for_publication", "in_review"],
                    ready_for_publication: ["published", "reviewed"],
                    published: ["submitted_to_records"],
                    submitted_to_records: ["closed"],
                    closed: [],
                  };
                  const nexts = nextMap[lifecycleRecord.status] ?? [];
                  if (nexts.length === 0) return null;
                  return (
                    <div className="flex gap-2 flex-wrap pt-1">
                      {nexts.map((s) => (
                        <Button
                          key={s}
                          size="sm"
                          variant={s === "published" || s === "submitted_to_records" || s === "closed" ? "default" : "outline"}
                          onClick={() => handleLifecycleTransition(s)}
                        >
                          → {s.replace(/_/g, " ")}
                        </Button>
                      ))}
                    </div>
                  );
                })()}
                {lifecycleRecord.published_ref && (
                  <p className="text-xs text-gray-500">
                    Published ref: <span className="font-mono">{lifecycleRecord.published_ref}</span>
                    {lifecycleRecord.published_venue && ` · ${lifecycleRecord.published_venue}`}
                    {lifecycleRecord.published_at && ` · ${lifecycleRecord.published_at}`}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* SLA Summary — Phase 8 */}
          {slaSummary && slaSummary.total > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-500" />
                    Review SLA Status
                  </span>
                  {canEdit && (
                    <Button size="sm" variant="outline" onClick={handleRunSlaReminders}>
                      Send SLA Reminders
                    </Button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4 flex-wrap text-sm">
                  <span className="flex items-center gap-1 text-green-700">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {slaSummary.on_track} on track
                  </span>
                  {slaSummary.due_soon > 0 && (
                    <span className="flex items-center gap-1 text-amber-600">
                      <Clock className="w-3.5 h-3.5" />
                      {slaSummary.due_soon} due soon
                    </span>
                  )}
                  {slaSummary.overdue > 0 && (
                    <span className="flex items-center gap-1 text-red-600 font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      {slaSummary.overdue} overdue
                      {slaSummary.max_overdue_days > 0 && ` (max ${slaSummary.max_overdue_days}d)`}
                    </span>
                  )}
                  {slaSummary.no_deadline > 0 && (
                    <span className="text-gray-400">{slaSummary.no_deadline} no deadline</span>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Document Quality Scores — only shown when FSV is enabled (Item 34 Phase 4) */}
          {fsvEnabled && qualityScores && qualityScores.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">
                  Document Quality Scores
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Document</TableHead>
                      <TableHead>Quality</TableHead>
                      <TableHead>Reading Level</TableHead>
                      <TableHead>Flesch Score</TableHead>
                      <TableHead>vs. Avg</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {qualityScores.map((ds) => {
                      const pct = Math.round(ds.quality_score * 100);
                      const color =
                        pct >= 80
                          ? "text-green-700 bg-green-50"
                          : pct >= 50
                            ? "text-amber-700 bg-amber-50"
                            : "text-red-700 bg-red-50";
                      const avg = ds.doc_type_avg_score;
                      const diff = avg != null ? ds.quality_score - avg : null;
                      return (
                        <TableRow key={ds.document_id}>
                          <TableCell className="font-mono text-xs truncate max-w-[200px]">
                            {ds.document_id}
                          </TableCell>
                          <TableCell>
                            <span className={cn("px-2 py-0.5 rounded text-sm font-semibold", color)}>
                              {pct}%
                            </span>
                          </TableCell>
                          <TableCell className="text-sm">
                            {ds.plain_language_grade}
                          </TableCell>
                          <TableCell className="text-sm">
                            {ds.flesch_reading_ease}
                          </TableCell>
                          <TableCell className="text-sm">
                            {diff != null ? (
                              <span className={diff > 0.02 ? "text-green-600" : diff < -0.02 ? "text-red-600" : "text-gray-500"}>
                                {diff > 0.02 ? "▲" : diff < -0.02 ? "▼" : "="}{" "}
                                {avg != null ? `${Math.round(avg * 100)}% avg` : ""}
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
                {qualityScores.some((ds) => ds.high_risk_terms.length > 0) && (
                  <p className="mt-2 text-xs text-amber-600">
                    ⚠ Some documents contain high-risk terms that may affect scoring.
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Workflow & progress */}
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Workflow
                  {!canAdvance && approvalsForPhase.some((a) => a.required !== false) && (
                    <span
                      className="text-xs font-normal text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full"
                      title="All required approvals must be complete before advancing"
                    >
                      Approvals required
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <WorkflowTimeline steps={timelineSteps} />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Current phase: {workflow?.phase}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Overall Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <ProgBar value={project.progress} />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  {project.progress}% complete
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Records Retention (NARA) — Phase 7 */}
          {canEdit && (
            <Disclosure>
              {({ open }) => (
                <>
                  <Disclosure.Button className="w-full text-left">
                    <h2 className="flex items-center gap-2 text-base font-semibold text-gray-700 dark:text-gray-300">
                      <LayoutList className="w-4 h-4 text-indigo-500" />
                      Records Retention (NARA){" "}
                      {open ? (
                        <ChevronDown className="w-4 h-4 ml-auto text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 ml-auto text-gray-400" />
                      )}
                    </h2>
                  </Disclosure.Button>
                  <Transition
                    show={open}
                    as={Fragment}
                    enter="transition ease-out duration-100"
                    enterFrom="transform opacity-0 scale-95"
                    enterTo="transform opacity-100 scale-100"
                    leave="transition ease-in duration-75"
                    leaveFrom="transform opacity-100 scale-100"
                    leaveTo="transform opacity-0 scale-95"
                  >
                    <Card>
                      <CardContent className="pt-4 space-y-4">
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          NARA records management metadata for this project. Required when
                          submitting to federal records systems.
                        </p>
                        <div className="grid sm:grid-cols-2 gap-4">
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                              Schedule Number
                            </label>
                            <Input
                              value={naraScheduleNumber}
                              onChange={(e) => setNaraScheduleNumber(e.target.value)}
                              placeholder="e.g. DAA-GRS-2017-0007"
                              className="text-sm"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                              Disposition Authority
                            </label>
                            <Input
                              value={naraDispositionAuthority}
                              onChange={(e) => setNaraDispositionAuthority(e.target.value)}
                              placeholder="e.g. N1-AU-04-18"
                              className="text-sm"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                              Retention Period
                            </label>
                            <Input
                              value={naraRetentionPeriod}
                              onChange={(e) => setNaraRetentionPeriod(e.target.value)}
                              placeholder="e.g. Permanent, 7 years after close"
                              className="text-sm"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                              Record Series
                            </label>
                            <Input
                              value={naraRecordSeries}
                              onChange={(e) => setNaraRecordSeries(e.target.value)}
                              placeholder="e.g. Policy Documents"
                              className="text-sm"
                            />
                          </div>
                        </div>
                        <div className="flex justify-end">
                          <Button
                            size="sm"
                            onClick={handleSaveNara}
                            disabled={savingNara}
                          >
                            {savingNara ? "Saving…" : "Save NARA Metadata"}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </Transition>
                </>
              )}
            </Disclosure>
          )}

          {/* Primary CTA + quality badge */}
          <div className="flex flex-col items-center gap-2">
            <Button asChild className="text-lg px-6 py-3 rounded-lg shadow-lg">
              <Link href={editorURL}>
                <FileEdit className="w-5 h-5 mr-2" />{" "}
                {project.editor === "word" ? "View" : "Edit"} Document
              </Link>
            </Button>
            {fsvEnabled && (() => {
              // Show quality badge for the primary document if scores are loaded
              const primaryScore = qualityScores?.find(
                (s) => s.document_id === project.id,
              );
              if (!primaryScore) return null;
              const pct = Math.round(primaryScore.quality_score * 100);
              const color =
                pct >= 80 ? "bg-green-100 text-green-800" :
                pct >= 50 ? "bg-amber-100 text-amber-800" :
                "bg-red-100 text-red-800";
              return (
                <span
                  title={`Quality score: ${pct}% | Grade: ${primaryScore.plain_language_grade} | Flesch: ${primaryScore.flesch_reading_ease}`}
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium cursor-default ${color}`}
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  Quality: {pct}% &nbsp;·&nbsp; Grade: {primaryScore.plain_language_grade}
                </span>
              );
            })()}
          </div>
        </section>

        {/* REVIEWERS SECTION — assignment lifecycle */}
        <section id="reviewers" className="space-y-6">
          <div className="flex justify-between items-center flex-wrap gap-2">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Users2 className="w-5 h-5" /> Reviewers
            </h2>
            <div className="flex gap-2">
              {canEdit && assignments.filter((a) => !["replaced","concurred","signed","declined"].includes(a.status)).length > 0 && (
                <Button size="sm" variant="outline" onClick={handleRemindAll}>
                  <Bell className="w-4 h-4 mr-1" /> Remind All
                </Button>
              )}
              {assignments.length > 0 && (
                <Button size="sm" variant="outline" onClick={handleExportReviewers}>
                  <Download className="w-4 h-4 mr-1" /> Export
                </Button>
              )}
            </div>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Reviewer assignments control who is invited, who can submit feedback, and who can sign off.
            Use this section first, then add a separate approval below only when the current phase also
            requires a formal approval record.
          </p>

          {/* Review progress summary */}
          {assignments.length > 0 && (() => {
            const active = assignments.filter((a) => a.status !== "replaced");
            const done = active.filter((a) => a.status === "concurred" || a.status === "signed");
            const pct = active.length > 0 ? Math.round((done.length / active.length) * 100) : 0;
            return (
              <div className="flex items-center gap-4 p-3 rounded-lg bg-gray-50 border">
                <span className="text-sm font-medium text-gray-700">
                  {done.length} / {active.length} reviewers complete
                </span>
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className={cn(
                      "h-2 rounded-full transition-all",
                      pct === 100 ? "bg-green-500" : pct >= 50 ? "bg-blue-500" : "bg-yellow-400",
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-sm font-semibold text-gray-600">{pct}%</span>
              </div>
            );
          })()}

          <Card>
            <CardContent className="space-y-4">
              {/* Add assignment form */}
              {canEdit && (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                  <div className="flex-1">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Invite reviewer
                    </label>
                    <UserPicker
                      value={assignmentReviewerInput}
                      onChange={setAssignmentReviewerInput}
                      placeholder="Search for a user…"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Due date (optional)
                    </label>
                    <input
                      type="date"
                      value={assignmentDueDate}
                      onChange={(e) => setAssignmentDueDate(e.target.value)}
                      className="block w-full rounded border px-2 py-2 text-sm"
                    />
                  </div>
                  <Button
                    size="sm"
                    onClick={handleAddAssignment}
                    disabled={!assignmentReviewerInput.trim() || addingAssignment}
                  >
                    <UserPlus className="w-4 h-4 mr-1" />
                    {addingAssignment ? "Inviting…" : "Invite"}
                  </Button>
                </div>
              )}

              {/* Assignment table */}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Reviewer</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Invited</TableHead>
                    <TableHead>Due</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assignments.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-sm text-gray-500 text-center py-6">
                        No reviewers assigned yet.
                      </TableCell>
                    </TableRow>
                  ) : (
                    assignments.map((a) => {
                      const statusColors: Record<string, string> = {
                        invited: "bg-gray-100 text-gray-600",
                        reviewing: "bg-blue-100 text-blue-700",
                        feedback_submitted: "bg-indigo-100 text-indigo-700",
                        concurred: "bg-green-100 text-green-700",
                        non_concurred: "bg-red-100 text-red-700",
                        signed: "bg-emerald-100 text-emerald-700",
                        declined: "bg-orange-100 text-orange-700",
                        replaced: "bg-gray-100 text-gray-400 line-through",
                      };
                      return (
                        <TableRow key={a.id} className={a.status === "replaced" ? "opacity-50" : ""}>
                          <TableCell className="font-medium">{a.reviewer}</TableCell>
                          <TableCell>
                            <span className={cn(
                              "px-2 py-0.5 rounded text-xs font-semibold",
                              statusColors[a.status] ?? "bg-gray-100 text-gray-600",
                            )}>
                              {a.status.replace(/_/g, " ")}
                            </span>
                          </TableCell>
                          <TableCell className="text-xs text-gray-500">
                            {a.requested_at ? new Date(a.requested_at).toLocaleDateString() : "—"}
                          </TableCell>
                          <TableCell className="text-xs">
                            {(() => {
                              const ds = slaDeadlines.find((d) => d.assignment_id === a.id);
                              if (!a.due_date) return <span className="text-gray-400">—</span>;
                              const label = new Date(a.due_date).toLocaleDateString();
                              if (!ds || ds.status === "complete" || ds.status === "no_deadline") {
                                return <span className="text-gray-500">{label}</span>;
                              }
                              if (ds.status === "overdue") {
                                return (
                                  <span className="text-red-600 font-semibold">
                                    {label} <span className="text-xs">({ds.overdue_days}d overdue)</span>
                                  </span>
                                );
                              }
                              if (ds.status === "due_soon") {
                                return (
                                  <span className="text-amber-600 font-medium">
                                    {label} <span className="text-xs">({ds.days_remaining}d left)</span>
                                  </span>
                                );
                              }
                              return (
                                <span className="text-green-600">
                                  {label} <span className="text-xs">({ds.days_remaining}d)</span>
                                </span>
                              );
                            })()}
                          </TableCell>
                          <TableCell className="text-right space-x-1">
                            {canEdit && a.status !== "replaced" && !["concurred","signed","declined"].includes(a.status) && (
                              <Button
                                size="sm"
                                variant="ghost"
                                title="Send reminder"
                                onClick={() => handleSendReminder(a.id)}
                              >
                                <Bell className="w-4 h-4" />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </section>

        {/* SIGNATURES SECTION — Phase 4/6 */}
        <section id="signatures" className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <CheckCircle2 className="w-5 h-5" /> Reviewer Sign-off &amp; Concurrence
            </h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            This section tracks each invited reviewer&apos;s review lifecycle after they have been assigned above.
            It is separate from phase approvals.
          </p>

          {assignments.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-gray-400 text-sm">
                No reviewer assignments yet. Invite reviewers in the Reviewers tab.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {assignments.filter((a) => a.status !== "replaced").map((a) => {
                const isTerminal = ["concurred", "signed", "declined", "non_concurred"].includes(a.status);
                const isMine = a.reviewer === username;
                const isEligible = eligibilityCache[a.id];

                const statusColors: Record<string, string> = {
                  invited: "bg-gray-100 text-gray-600",
                  reviewing: "bg-blue-100 text-blue-700",
                  feedback_submitted: "bg-indigo-100 text-indigo-700",
                  concurred: "bg-green-100 text-green-700",
                  non_concurred: "bg-red-100 text-red-700",
                  signed: "bg-emerald-100 text-emerald-700",
                  declined: "bg-orange-100 text-orange-700",
                };

                return (
                  <Card key={a.id} className={cn(isTerminal ? "border-green-200" : "")}>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-3 flex-wrap">
                        <div className="flex-1 min-w-[160px]">
                          <p className="font-medium">{a.reviewer}</p>
                          <p className="text-xs text-gray-500">
                            Invited {new Date(a.requested_at).toLocaleDateString()}
                            {a.due_date && (
                              <span className={cn(
                                "ml-2",
                                new Date(a.due_date) < new Date() && !isTerminal
                                  ? "text-red-600 font-semibold"
                                  : "",
                              )}>
                                · Due {new Date(a.due_date).toLocaleDateString()}
                                {new Date(a.due_date) < new Date() && !isTerminal && " (overdue)"}
                              </span>
                            )}
                          </p>
                        </div>

                        <span className={cn(
                          "px-2 py-0.5 rounded text-xs font-semibold",
                          statusColors[a.status] ?? "bg-gray-100 text-gray-600",
                        )}>
                          {a.status.replace(/_/g, " ")}
                        </span>

                        {a.signed_at && (
                          <span className="text-xs text-green-600 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" />
                            Signed {new Date(a.signed_at).toLocaleDateString()}
                          </span>
                        )}

                        {/* Reviewer's own sign-off actions */}
                        {isMine && !isTerminal && (
                          <div className="flex gap-2 flex-wrap ml-auto">
                            {isEligible?.eligible ? (
                              <>
                                <Button
                                  size="sm"
                                  className="bg-green-600 hover:bg-green-700 text-white"
                                  onClick={() => handleConcur(a.id)}
                                >
                                  <CheckCircle2 className="w-3 h-3 mr-1" /> Concur
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="text-indigo-700 border-indigo-300"
                                  onClick={() => handleConcurWithComments(a.id)}
                                >
                                  <MessageSquare className="w-3 h-3 mr-1" /> Concur w/ Comments
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleSignInternal(a.id)}
                                >
                                  Internal Sign-off
                                </Button>
                              </>
                            ) : isEligible !== undefined && !isEligible.eligible ? (
                              <span className="text-xs text-amber-600 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {(isEligible.unanswered_questions ?? 0) > 0
                                  ? `Waiting for SME: ${isEligible.unanswered_questions} unanswered question(s)`
                                  : `${isEligible.open_items} open feedback item(s)`}
                              </span>
                            ) : null}
                          </div>
                        )}

                        {/* SME/admin actions */}
                        {canEdit && !isTerminal && (
                          <div className="flex gap-1 flex-wrap ml-auto">
                            {!isMine && (
                              <>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  title="Request concurrence"
                                  onClick={() => handleRequestConcurrence(a.id)}
                                >
                                  <CheckCircle2 className="w-4 h-4 text-indigo-500" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  title="Send reminder"
                                  onClick={() => handleSendReminder(a.id)}
                                >
                                  <Bell className="w-4 h-4" />
                                </Button>
                              </>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Non-concurrence reason */}
                      {a.status === "non_concurred" && a.replacement_reason && (
                        <p className="mt-2 text-sm text-red-600 italic ml-1">
                          Non-concurrence reason: {a.replacement_reason}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </section>

        <section id="approvals" className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Users2 className="w-5 h-5" /> Approvals
            </h2>
              {isOwner && (
                <div className="flex gap-2">
                  <Button size="sm" onClick={downloadApprovalSummary}>
                    <Download className="w-4 h-4 mr-1" /> Download Summary
                  </Button>
                  <Button size="sm" onClick={() => sendReminder()}>
                    <Mail className="w-4 h-4 mr-1" /> Remind Pending
                  </Button>
                </div>
              )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Approvals are optional phase-specific signoffs. A reviewer can be invited to review without also
            being added here. Add an approval only when the current phase requires one.
          </p>
          <Card>
            <CardContent className="space-y-4 overflow-x-auto">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Add approval for reviewer
                  </label>
                  <Input
                    list="approval-reviewer-options"
                    value={approvalReviewerInput}
                    onChange={(e) => setApprovalReviewerInput(e.target.value)}
                    placeholder="Select an invited reviewer"
                    disabled={!canEdit}
                  />
                  <datalist id="approval-reviewer-options">
                    {approvalReviewerOptions.map((name: string) => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>
                </div>
                <Button
                  size="sm"
                  onClick={handleAddApproval}
                  disabled={!canEdit || !approvalReviewerInput.trim() || addingApproval}
                >
                  <UserPlus className="w-4 h-4 mr-1" /> {addingApproval ? "Adding..." : "Add approval"}
                </Button>
              </div>
              {approvalActionError ? (
                <p className="text-sm text-red-600 dark:text-red-400">{approvalActionError}</p>
              ) : null}
              <ApprovalTable
                approvals={approvalsForPhase}
                currentUser={username}
                canEdit={canEdit}
                onSign={signApproval}
                onSignInitials={signApprovalByInitials}
                onReset={resetApprovalLocal}
                onRemove={removeApproval}
                onBulkReminder={(ids) => sendReminder(ids)}
                onHistory={viewHistory}
              />
            </CardContent>
          </Card>
        </section>

        {/* FEEDBACK SECTION — unified ledger */}
        <section id="feedback" className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <MessageSquare className="w-5 h-5" /> Feedback Ledger
            </h2>
            <Button asChild variant="outline" size="sm">
              <Link
                href={`/projects/${id}#feedback`}
                title="Jump to the Feedback tab for this project"
              >
                Open review workspace
              </Link>
            </Button>
          </div>

          {/* Progress bar */}
          {feedbackProgress && feedbackProgress.total > 0 && (
            <div className="p-3 rounded-lg bg-gray-50 border space-y-1">
              <div className="flex justify-between text-sm font-medium">
                <span>{feedbackProgress.addressed} of {feedbackProgress.total} items addressed</span>
                <span className="text-gray-500">
                  {feedbackProgress.open} open · {feedbackProgress.accepted} accepted ·{" "}
                  {feedbackProgress.rejected} rejected · {feedbackProgress.resolved} resolved
                </span>
              </div>
              <ProgBar value={feedbackProgress.total > 0 ? Math.round((feedbackProgress.addressed / feedbackProgress.total) * 100) : 0} />
            </div>
          )}

          {/* Post feedback */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Post Feedback</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                {(["comment", "question", "suggestion", "non_concurrence"] as const).map((t) => {
                  const icons: Record<string, React.ReactNode> = {
                    comment: <MessageSquare className="w-3 h-3" />,
                    question: <HelpCircle className="w-3 h-3" />,
                    suggestion: <Lightbulb className="w-3 h-3" />,
                    non_concurrence: <AlertTriangle className="w-3 h-3" />,
                  };
                  return (
                    <button
                      key={t}
                      onClick={() => setNewFeedbackType(t)}
                      className={cn(
                        "flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border",
                        newFeedbackType === t
                          ? "bg-indigo-600 text-white border-indigo-600"
                          : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400",
                      )}
                    >
                      {icons[t]} {t.replace(/_/g, " ")}
                    </button>
                  );
                })}
              </div>
              <div className="flex gap-2">
                <input
                  className="flex-1 rounded border px-3 py-2 text-sm"
                  placeholder={`Add a ${newFeedbackType.replace(/_/g, " ")}…`}
                  value={newFeedbackText}
                  onChange={(e) => setNewFeedbackText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handlePostFeedback(); } }}
                />
                <Button size="sm" onClick={handlePostFeedback} disabled={!newFeedbackText.trim()}>
                  Submit
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* My-feedback toggle (Phase 5) */}
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={feedbackShowMyOnly}
                onChange={(e) => setFeedbackShowMyOnly(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                My feedback only
              </span>
            </label>
            <span className="text-xs text-gray-400">
              {feedbackShowMyOnly ? `Showing ${username}'s items` : "Showing all reviewers"}
            </span>
          </div>

          {/* Filters */}
          <div className="flex gap-2 flex-wrap">
            {["all", "comment", "question", "suggestion", "non_concurrence"].map((t) => (
              <button
                key={t}
                onClick={() => setFeedbackTypeFilter(t)}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-medium border",
                  feedbackTypeFilter === t
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300",
                )}
              >
                {t === "all" ? "All types" : t.replace(/_/g, " ")}
              </button>
            ))}
            <div className="ml-auto flex gap-2">
              {["all", "open", "accepted", "rejected", "resolved"].map((s) => (
                <button
                  key={s}
                  onClick={() => setFeedbackStatusFilter(s)}
                  className={cn(
                    "px-3 py-1 rounded-full text-xs font-medium border",
                    feedbackStatusFilter === s
                      ? "bg-gray-800 text-white border-gray-800"
                      : "bg-white text-gray-600 border-gray-200 hover:border-gray-400",
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Feedback items table */}
          {(() => {
            const topLevel = feedbackItems.filter((f) => !f.parent_id);
            const filtered = topLevel.filter((f) => {
              if (feedbackShowMyOnly && f.reviewer !== username) return false;
              if (feedbackTypeFilter !== "all" && f.feedback_type !== feedbackTypeFilter) return false;
              if (feedbackStatusFilter !== "all" && f.status !== feedbackStatusFilter) return false;
              return true;
            });

            if (filtered.length === 0) {
              return (
                <Card>
                  <CardContent className="py-10 text-center text-gray-400 text-sm">
                    No feedback items yet.
                  </CardContent>
                </Card>
              );
            }

            const typeIcon: Record<string, React.ReactNode> = {
              comment: <MessageSquare className="w-4 h-4 text-blue-500" />,
              question: <HelpCircle className="w-4 h-4 text-yellow-500" />,
              suggestion: <Lightbulb className="w-4 h-4 text-purple-500" />,
              non_concurrence: <AlertTriangle className="w-4 h-4 text-red-500" />,
            };
            const statusBadge: Record<string, string> = {
              open: "bg-gray-100 text-gray-600",
              accepted: "bg-green-100 text-green-700",
              rejected: "bg-red-100 text-red-700",
              resolved: "bg-blue-100 text-blue-700",
            };

            return (
              <div className="space-y-3">
                {filtered.map((item) => {
                  const isExpanded = expandedFeedback.has(item.id);
                  const replies = feedbackItems.filter((f) => f.parent_id === item.id);
                  const isTerminal = ["accepted", "rejected", "resolved"].includes(item.status);
                  return (
                    <Card key={item.id} className={cn(isTerminal ? "opacity-80" : "")}>
                      <CardContent className="pt-4 space-y-3">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5">{typeIcon[item.feedback_type] ?? <MessageSquare className="w-4 h-4" />}</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-sm">{item.reviewer}</span>
                              <span className={cn("px-2 py-0.5 rounded text-xs font-semibold", statusBadge[item.status] ?? "bg-gray-100 text-gray-600")}>
                                {item.status}
                              </span>
                              <span className="text-xs text-gray-400">
                                {item.feedback_type.replace(/_/g, " ")}
                              </span>
                              {item.phase && (
                                <span className="text-xs text-gray-400 italic">{item.phase}</span>
                              )}
                              <span className="text-xs text-gray-400 ml-auto">
                                {new Date(item.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            <p className="text-sm mt-1">{item.text}</p>
                            {item.disposition_reason && (
                              <p className="text-xs text-gray-500 mt-1 italic">
                                Reason: {item.disposition_reason}
                              </p>
                            )}
                          </div>
                          <button
                            className="ml-2 text-gray-400 hover:text-gray-600"
                            onClick={() => setExpandedFeedback((prev) => {
                              const next = new Set(prev);
                              next.has(item.id) ? next.delete(item.id) : next.add(item.id);
                              return next;
                            })}
                            title={isExpanded ? "Collapse" : "Expand thread"}
                          >
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                        </div>

                        {/* Threaded replies */}
                        {isExpanded && (
                          <div className="ml-7 space-y-2 border-l-2 border-gray-100 pl-4">
                            {replies.map((r) => (
                              <div key={r.id} className="text-sm">
                                <span className="font-medium">{r.reviewer}:</span>{" "}
                                <span>{r.text}</span>
                                <span className="text-xs text-gray-400 ml-2">
                                  {new Date(r.created_at).toLocaleDateString()}
                                </span>
                              </div>
                            ))}
                            {/* Reply input */}
                            <div className="flex gap-2 mt-2">
                              <input
                                className="flex-1 rounded border px-2 py-1 text-sm"
                                placeholder="Reply…"
                                value={replyText[item.id] ?? ""}
                                onChange={(e) => setReplyText((prev) => ({ ...prev, [item.id]: e.target.value }))}
                                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleReply(item.id); } }}
                              />
                              <Button size="sm" variant="outline" onClick={() => handleReply(item.id)}>
                                Reply
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Disposition actions — SME/admin only */}
                        {canEdit && !isTerminal && (
                          <div className="flex gap-2 ml-7 flex-wrap">
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-green-700 border-green-300 hover:bg-green-50"
                              onClick={() => handleDisposition(item.id, "accepted")}
                            >
                              <CheckCircle2 className="w-3 h-3 mr-1" /> Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-blue-700 border-blue-300 hover:bg-blue-50"
                              onClick={() => handleDisposition(item.id, "resolved")}
                            >
                              <CheckCircle2 className="w-3 h-3 mr-1" /> Resolve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-700 border-red-300 hover:bg-red-50"
                              onClick={() => {
                                const reason = window.prompt("Reason for rejection:");
                                if (reason !== null) handleDisposition(item.id, "rejected", reason);
                              }}
                            >
                              <XCircle className="w-3 h-3 mr-1" /> Reject
                            </Button>
                          </div>
                        )}

                        {/* Question satisfied button — reviewer only */}
                        {item.feedback_type === "question" && item.reviewer === username && !item.question_satisfied && (
                          <div className="ml-7">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={async () => {
                                await authenticatedFetch(
                                  `/projects/${id}/feedback/${item.id}/question-satisfied`,
                                  { method: "POST" },
                                );
                                refetchFeedback();
                                toast.success("Marked as satisfied.");
                              }}
                            >
                              <CheckCircle2 className="w-3 h-3 mr-1" /> Mark satisfied
                            </Button>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            );
          })()}

          {/* Inline reviewer comments (legacy) */}
          <Disclosure>
            {({ open }) => (
              <>
                <Disclosure.Button className="w-full text-left">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-600">
                    <LayoutList className="w-4 h-4" /> Inline Document Comments{" "}
                    {open ? "" : "(collapsed)"}
                  </h3>
                </Disclosure.Button>
                <Transition
                  show={open}
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <Card>
                    <CardContent className="pt-4">
                      <ReviewerComments
                        docId={project.id}
                        currentUser={username ?? ""}
                        canDispose={canEdit}
                      />
                    </CardContent>
                  </Card>
                </Transition>
              </>
            )}
          </Disclosure>
        </section>

        {/* HISTORY SECTION */}
        <section id="history" className="space-y-6">
          <Disclosure defaultOpen>
            {({ open }) => (
              <>
                <Disclosure.Button className="w-full text-left">
                  <h2 className="flex items-center gap-2 text-lg font-semibold">
                    <History className="w-5 h-5" /> Audit History{" "}
                    {open ? "" : "(collapsed)"}
                  </h2>
                </Disclosure.Button>
                <Transition
                  show={open}
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <AuditTimeline events={auditEvents} />
                </Transition>
              </>
            )}
          </Disclosure>

          {/* Notification log */}
          {notifLog.length > 0 && (
            <Disclosure>
              {({ open }) => (
                <>
                  <Disclosure.Button className="w-full text-left">
                    <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-600">
                      <Bell className="w-4 h-4" /> Notification Log{" "}
                      {open ? "" : `(${notifLog.length} events, collapsed)`}
                    </h3>
                  </Disclosure.Button>
                  <Transition
                    show={open}
                    as={Fragment}
                    enter="transition ease-out duration-100"
                    enterFrom="transform opacity-0 scale-95"
                    enterTo="transform opacity-100 scale-100"
                    leave="transition ease-in duration-75"
                    leaveFrom="transform opacity-100 scale-100"
                    leaveTo="transform opacity-0 scale-95"
                  >
                    <Card>
                      <CardContent className="pt-4">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Event</TableHead>
                              <TableHead>Reviewer</TableHead>
                              <TableHead>Message</TableHead>
                              <TableHead>Sent</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {notifLog.map((n) => (
                              <TableRow key={n.id}>
                                <TableCell className="text-xs font-mono">{n.event}</TableCell>
                                <TableCell className="text-xs">{n.reviewer ?? "—"}</TableCell>
                                <TableCell className="text-xs max-w-xs truncate">{n.message}</TableCell>
                                <TableCell className="text-xs text-gray-400">
                                  {new Date(n.sent_at).toLocaleString()}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  </Transition>
                </>
              )}
            </Disclosure>
          )}
        </section>

        {/* RECORDS SECTION — visible when submitted_to_records or closed (Phase 7) */}
        {lifecycleRecord && ["submitted_to_records", "closed", "published", "ready_for_publication"].includes(lifecycleRecord.status) && (
          <section id="records" className="space-y-4">
            <div className="flex justify-between items-center flex-wrap gap-2">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Download className="w-5 h-5 text-indigo-600" /> Records &amp; Retention
              </h2>
              {canEdit && (
                <Button size="sm" onClick={handleDownloadRecordsPackage}>
                  <Download className="w-4 h-4 mr-1" /> Download Review Record Package
                </Button>
              )}
            </div>
            <Card>
              <CardContent className="pt-4 space-y-3 text-sm">
                <div className="grid sm:grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Lifecycle Status</p>
                    <p className="font-semibold mt-0.5">{lifecycleRecord.status.replace(/_/g, " ")}</p>
                  </div>
                  {lifecycleRecord.published_ref && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Publication Reference</p>
                      <p className="font-mono mt-0.5">{lifecycleRecord.published_ref}</p>
                    </div>
                  )}
                  {lifecycleRecord.published_venue && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Publication Venue</p>
                      <p className="mt-0.5">{lifecycleRecord.published_venue}</p>
                    </div>
                  )}
                  {lifecycleRecord.published_at && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Publication Date</p>
                      <p className="mt-0.5">{lifecycleRecord.published_at}</p>
                    </div>
                  )}
                  {lifecycleRecord.set_by && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Last Updated By</p>
                      <p className="mt-0.5">{lifecycleRecord.set_by}</p>
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-400">
                  The review record package contains the complete feedback ledger, reviewer assignments,
                  signature history, notifications, NARA metadata, and document versions in a
                  ZIP archive with an integrity hash for records retention compliance.
                </p>
              </CardContent>
            </Card>
          </section>
        )}
      </div>

      {/* Modals */}
      <PhaseAdvanceModal
        open={showPhaseDialog}
        onClose={() => setShowPhaseDialog(false)}
        onConfirm={confirmPhaseChange}
        approvals={approvalsForPhase}
        checks={
          PHASE_CHECKS[project.currentPhaseId || workflow?.phase || ""] || []
        }
      />
      <VersionDrawer
        open={showVersions}
        onClose={() => setShowVersions(false)}
        versions={versions}
      />
      <Dialog open={showHistory} onOpenChange={setShowHistory}>
        <DialogContent className="max-w-md" onKeyDown={(e) => e.key === "Escape" && setShowHistory(false)}>
          <DialogHeader>
            <DialogTitle>Approval History</DialogTitle>
          </DialogHeader>
          <AuditTimeline events={historyEvents} />
        </DialogContent>
      </Dialog>
    </>
  );
}
