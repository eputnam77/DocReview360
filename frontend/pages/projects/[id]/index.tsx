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
import { API, authenticatedFetch } from "@/lib/api";
import { ApprovalTable, AuditTimeline, ProjectSummaryBar, KpiCards, PhaseAdvanceModal, WorkflowTimeline, ReviewerComments } from "@/components";
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
    Trash2
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

// ---------------------------------------------------------------------------
// 1 ▲ Types
// ---------------------------------------------------------------------------
interface Project {
  id: string;
  number: string | number;
  type: string;
  title: string;
  owner: string;
  status: string;
  progress: number;
  updated?: string;
  editor?: string;
  workflow?: string;
  currentPhaseId?: string | null;
}
interface LogEntry {
  id: string;
  timestamp: string;
  action: string;
  type: "approval" | "review" | "edit" | "phase";
  ref?: string;
}
interface WorkflowStep {
  name: string;
  status?: "complete" | "active" | "pending";
}
interface Workflow {
  id: string;
  phase: string;
  steps?: WorkflowStep[];
}
interface Approval {
  id: string;
  reviewer: string;
  email: string;
  state: "pending" | "approved" | "overdue" | "rejected";
  dueAt: string;
  signedAt?: string;
  comments?: string;
  documensoSigId?: string;
  description?: string; // Description from the approval step
  phaseId?: string;
  required?: boolean;
}
interface VersionEntry {
  id: string;
  timestamp: string;
  author: string;
  action: string;
}

// Utility helpers
// ---------------------------------------------------------------------------
const slug = (s: string) => s.toLowerCase().replace(/\s+/g, "");
function classNames(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
function ProgBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
      <div
        className={cn(
          "h-2 rounded-full transition-all",
          pct === 100
            ? "bg-green-500"
            : pct >= 70
              ? "bg-blue-500"
              : pct > 0
                ? "bg-yellow-400"
                : "bg-gray-400",
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// Sticky nav
const NAV = [
  { id: "details", label: "Details" },
  { id: "approvals", label: "Approvals" },
  { id: "reviews", label: "Reviews" },
  { id: "history", label: "History" },
];

const PHASE_CHECKS: Record<string, string[]> = {
  draft: ["Draft completed"],
  review: ["Review feedback addressed"],
  approval: ["Approval package prepared"],
};
function StickyNav() {
  const [active, setActive] = React.useState(NAV[0].id);
  const linksRef = React.useRef<(HTMLAnchorElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLUListElement>) => {
    const idx = NAV.findIndex((n) => n.id === active);
    let newIdx = idx;
    if (e.key === "ArrowRight") {
      newIdx = (idx + 1) % NAV.length;
    } else if (e.key === "ArrowLeft") {
      newIdx = (idx - 1 + NAV.length) % NAV.length;
    } else if (e.key === "Home") {
      newIdx = 0;
    } else if (e.key === "End") {
      newIdx = NAV.length - 1;
    } else {
      return;
    }
    e.preventDefault();
    const newTab = NAV[newIdx];
    setActive(newTab.id);
    linksRef.current[newIdx]?.focus();
  };

  return (
    <nav className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur supports-backdrop-blur:border-b supports-backdrop-blur:border-gray-200 dark:supports-backdrop-blur:border-gray-700">
      <ul
        role="tablist"
        className="flex gap-6 px-8 py-2 text-sm font-medium overflow-x-auto scrollbar-hide"
        onKeyDown={handleKeyDown}
      >
        {NAV.map((s, i) => (
          <li key={s.id}>
            <a
              ref={(el) => {
                linksRef.current[i] = el;
              }}
              role="tab"
              id={`nav-${s.id}`}
              aria-selected={active === s.id}
              tabIndex={active === s.id ? 0 : -1}
              href={`#${s.id}`}
              className="hover:text-indigo-600 dark:hover:text-indigo-400 text-gray-600 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              onClick={() => setActive(s.id)}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault();
                  setActive(s.id);
                  linksRef.current[i]?.click();
                }
              }}
            >
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}


// Version timeline drawer (roadmap)
function VersionDrawer({
  open,
  onClose,
  versions,
}: {
  open: boolean;
  onClose: () => void;
  versions: VersionEntry[];
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent
        role="dialog"
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        className="max-w-md sm:max-w-md"
      >
        <DialogHeader>
          <DialogTitle>Document Versions</DialogTitle>
        </DialogHeader>
        <ul className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
          {versions.map((v) => (
            <li key={v.id} className="relative pl-6">
              <span className="absolute left-0 top-1.5 w-3 h-3 bg-indigo-600 rounded-full" />
              <p className="text-sm font-medium">{v.action}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {v.timestamp} — {v.author}
              </p>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

// ----------------------------------------------------------------------------
// 4 ▲ Main component
// ----------------------------------------------------------------------------
export default function ProjectDetailsPage() {
  const router = useRouter();
  const { id } = router.query;

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

  const approvalsForPhase = useMemo(
    () =>
      approvals.filter(
        (a) => !project?.currentPhaseId || a.phaseId === project.currentPhaseId,
      ),
    [approvals, project?.currentPhaseId],
  );

  const [showVersions, setShowVersions] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

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
  const { data: projectData, isLoading: projectLoading } = useProject(id as string);
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
      const res = await authenticatedFetch(`${API}/users`);
      if (!res.ok) return [];
      return res.json();
    },
  });

  const reviewerOptions = useMemo(
    () =>
      userOptions
        .filter((u: any) => Array.isArray(u.roles) && u.roles.includes("reviewer"))
        .map((u: any) => u.username),
    [userOptions],
  );

  useEffect(() => {
    setProject(projectData ?? null);
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
    authenticatedFetch(`${API}/audit?entity_id=${id}`)
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

  const auditEvents = useMemo(
    () =>
      logs.map((l) => ({
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
      })),
    [logs, id],
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
        const res = await authenticatedFetch(`${API}/projects/${project.id}`, {
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

      const response = await authenticatedFetch(`${API}/approvals`, {
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
    if (!reviewers.includes(reviewer)) {
      const message = "Reviewer must be assigned to the project first.";
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
  }, [approvalReviewerInput, createApprovalForReviewer, reviewers]);

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

  const sendReminder = (ids?: string[]) => {
    const targets = approvalsForPhase.filter(
      (a) =>
        (ids ? ids.includes(a.id) : true) &&
        (a.state === "pending" || a.state === "overdue"),
    );
    remind(targets.map((a) => a.id));
  };

  const viewHistory = useCallback((aid: string) => {
    authenticatedFetch(`${API}/approvals/${aid}/history`)
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
      const res = await authenticatedFetch(`${API}/approvals/${aid}/sign-initials`, {
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
      const response = await authenticatedFetch(`${API}/approvals/${aid}`, {
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
      const response = await authenticatedFetch(`${API}/approvals/${approvalId}`, {
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
      const res = await authenticatedFetch(`${API}/projects/${project.id}/approvals/pdf`);
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
  if (!project) return <p className="p-4">Project not found.</p>;

  const editorURL = `/editors/${project.editor ?? "tiptap"}?projectId=${project.id}`;

  // ------------------------------------------------------------------------
  //                             RENDER
  // ------------------------------------------------------------------------
  return (
    <>
      <StickyNav />
      <div className="p-8 space-y-10">
        <ProjectSummaryBar
          project={{ ...project, currentPhaseId: project.currentPhaseId || workflow?.phase }}
          phases={phaseList}
          phaseCounts={phaseCounts}
          onPhaseChange={canEdit ? requestPhaseChange : undefined}
          onExportRaci={isOwner ? exportRaci : undefined}
          onShowVersions={() => setShowVersions(true)}
          isOwner={isOwner}
        />

        {/* DETAILS SECTION */}
        <section id="details" className="space-y-6">
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

          {/* Primary CTA */}
          <div className="flex justify-center">
            <Button asChild className="text-lg px-6 py-3 rounded-lg shadow-lg">
              <Link href={editorURL}>
                <FileEdit className="w-5 h-5 mr-2" />{" "}
                {project.editor === "word" ? "View" : "Edit"} Document
              </Link>
            </Button>
          </div>
        </section>

        {/* REVIEWERS SECTION */}
        <section id="reviewers" className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Users2 className="w-5 h-5" /> Reviewers
            </h2>
          </div>
          <Card>
            <CardContent className="space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Add reviewer
                  </label>
                  <Input
                    list="reviewer-options"
                    value={reviewerInput}
                    onChange={(e) => setReviewerInput(e.target.value)}
                    placeholder="Select reviewer"
                    disabled={!canEdit}
                  />
                  <datalist id="reviewer-options">
                    {reviewerOptions.map((name: string) => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>
                </div>
                <Button
                  size="sm"
                  onClick={handleAddReviewer}
                  disabled={!canEdit || !reviewerInput.trim() || addingReviewer}
                >
                  <UserPlus className="w-4 h-4 mr-1" /> {addingReviewer ? "Adding..." : "Add"}
                </Button>
              </div>
              {reviewerActionError ? (
                <p className="text-sm text-red-600 dark:text-red-400">{reviewerActionError}</p>
              ) : null}
              {!reviewersLoading && reviewerOptions.length === 0 ? (
                <p className="text-xs text-amber-600 dark:text-amber-400">No reviewer users found in the system.</p>
              ) : null}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Reviewer</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reviewersLoading ? (
                    <TableRow>
                      <TableCell colSpan={2} className="text-sm text-gray-500">
                        Loading reviewers...
                      </TableCell>
                    </TableRow>
                  ) : reviewers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={2} className="text-sm text-gray-500">
                        No reviewers assigned yet.
                      </TableCell>
                    </TableRow>
                  ) : (
                    reviewers.map((reviewer) => (
                      <TableRow key={reviewer}>
                        <TableCell>
                          {editingReviewer === reviewer ? (
                            <Input
                              value={editingValue}
                              onChange={(e) => setEditingValue(e.target.value)}
                              placeholder="Reviewer name"
                              disabled={!canEdit}
                            />
                          ) : (
                            <span className="font-medium">{reviewer}</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right space-x-2">
                          {editingReviewer === reviewer ? (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={handleUpdateReviewer}
                                disabled={!canEdit || !editingValue.trim()}
                              >
                                Save
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setEditingReviewer(null);
                                  setEditingValue("");
                                }}
                              >
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setEditingReviewer(reviewer);
                                  setEditingValue(reviewer);
                                }}
                                disabled={!canEdit}
                              >
                                <Pencil className="w-4 h-4 mr-1" /> Edit
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleRemoveReviewer(reviewer)}
                                disabled={!canEdit}
                              >
                                <Trash2 className="w-4 h-4 mr-1" /> Remove
                              </Button>
                            </>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              <p className="text-xs text-gray-500">
                Reviewers are linked to this project and receive approval tasks.
              </p>
            </CardContent>
          </Card>
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
                    placeholder="Select assigned reviewer"
                    disabled={!canEdit}
                  />
                  <datalist id="approval-reviewer-options">
                    {reviewers.map((name: string) => (
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

        {/* REVIEW SUMMARY SECTION */}
        <section id="reviews" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Review summary</CardTitle>
            </CardHeader>
            <CardContent className="flex justify-between items-center">
              <span className="text-sm text-gray-500">
                {reviewCount} reviews in this phase
              </span>
              <Button asChild>
                <Link href={`/projects/${id}/review`}>
                  Open review workspace
                </Link>
              </Button>
            </CardContent>
          </Card>
        </section>

        {/* COMMENTS SECTION */}
        <section id="comments" className="space-y-6">
          <Disclosure>
            {({ open }) => (
              <>
                <Disclosure.Button className="w-full text-left">
                  <h2 className="flex items-center gap-2 text-lg font-semibold">
                    <LayoutList className="w-5 h-5" /> Reviewer Comments{" "}
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
        </section>
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

