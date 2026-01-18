// frontend/pages/projects/[id]/index.tsx
"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { API, authenticatedFetch } from "@/lib/api";
import { ApprovalTable, AuditTimeline, ProjectSummaryBar, KpiCards, PhaseAdvanceModal } from "@/components";
import type { AuditEntry } from "@/components/AuditTimeline";
import { cn } from "@/lib/utils";
import { useProject } from "@/lib/useProject";
import { usePhases } from "@/lib/usePhases";
import { useApprovals } from "@/lib/useApprovals";
import { useReviewSummary } from "@/lib/useReviewSummary";
import { useUserStore } from "@/state/user";
import { Disclosure, Transition } from "@headlessui/react";
import {
    FileEdit,
    History,
    LayoutList,
    Download,
    Mail,
    Users2
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
  status: "Draft" | "In Progress" | "Complete" | "Overdue";
  progress: number;
  updated?: string;
  editor?: "tiptap" | "word";
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
  status: "complete" | "active" | "pending";
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
interface Reply {
  id: string;
  author: string;
  text: string;
  date: string;
}
interface DispoComment {
  id: string;
  reviewer: string;
  routing: string;
  email: string;
  pagePara: string;
  comment: string;
  change: string;
  disposition: string;
  decision?: "Accepted" | "Rejected" | "Deferred" | "";
  replies?: Reply[];
}
interface RefDoc {
  name: string;
  url: string;
  type: string;
  file?: File;
}
interface VersionEntry {
  id: string;
  timestamp: string;
  author: string;
  action: string;
}

// ---------------------------------------------------------------------------
// Demo Data
// ---------------------------------------------------------------------------
const DEMO_PROJECT: Project = {
  id: "123e-ac-101",
  number: "AC 20-197",
  type: "Advisory Circular",
  title: "Turbine Engine and Airframe Sensor Icing Compliance",
  status: "In Progress",
  progress: 40,
  updated: "2025-07-04",
  owner: "Jane Doe",
  editor: "tiptap",
  currentPhaseId: "Review",
};

const DEMO_WORKFLOW: Workflow = {
  id: "wf-101",
  phase: "Review",
  steps: [
    { name: "Draft", status: "complete" },
    { name: "Review", status: "active" },
    { name: "Approval", status: "pending" },
    { name: "Published", status: "pending" },
  ],
};

const DEMO_APPROVALS: Approval[] = [
  {
    id: "appr-1",
    reviewer: "Jane Doe",
    email: "jane@example.com",
    state: "pending",
    dueAt: "2025-07-04",
    comments: "Please check the legal cites.",
    phaseId: "Review",
  },
  {
    id: "appr-2",
    reviewer: "John Smith",
    email: "john@example.com",
    state: "approved",
    dueAt: "2025-07-05",
    signedAt: "2025-07-05T14:30:00Z",
    comments: "Approved, no changes needed.",
    phaseId: "Review",
  },
];

const DEMO_DISPO_COMMENTS: DispoComment[] = [
  {
    id: "c1",
    reviewer: "Jane Doe",
    routing: "Legal",
    email: "jane@example.com",
    pagePara: "2/3.1",
    comment: "Clarify regulatory reference.",
    change: "Rewrite as: 'per 14 CFR 21.8…'",
    disposition: "Accepted",
    decision: "Accepted",
    replies: [
      {
        id: "r1",
        author: "Project Owner",
        text: "Addressed in rev-3.",
        date: "2025-07-05",
      },
    ],
  },
];

const DEMO_LOGS: LogEntry[] = [
  { timestamp: "2025-07-04", action: "Draft created", id: "l1", type: "edit" },
  { timestamp: "2025-07-04", action: "Initial review started", id: "l2", type: "review" },
  { timestamp: "2025-07-05", action: "Draft updated", id: "l3", type: "edit" },
];

const DEMO_APPROVAL_HISTORY: AuditEntry[] = [
  {
    id: "h1",
    timestamp: "2025-07-05T14:31:00Z",
    message: "signature_verified",
    type: "approval",
  },
  {
    id: "h2",
    timestamp: "2025-07-05T14:32:00Z",
    message: "signature_hash_mismatch",
    type: "approval",
  },
];

const DEMO_REFERENCE_DOCS: RefDoc[] = [
  {
    name: "Requirements.pdf",
    url: "https://file-examples.com/wp-content/uploads/2017/10/file-sample_150kB.pdf",
    type: "pdf",
  },
];

const DEMO_VERSIONS: VersionEntry[] = [
  {
    id: "v1",
    timestamp: "2025-07-04T10:00",
    author: "Jane Doe",
    action: "Draft uploaded",
  },
  {
    id: "v2",
    timestamp: "2025-07-04T18:30",
    author: "John Smith",
    action: "Minor edits",
  },
  {
    id: "v3",
    timestamp: "2025-07-05T09:15",
    author: "Jane Doe",
    action: "Address Legal comments",
  },
];

// ---------------------------------------------------------------------------
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
              ref={(el) => (linksRef.current[i] = el)}
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
  const [project, setProject] = useState<Project | null>(DEMO_PROJECT);
  const [workflow, setWorkflow] = useState<Workflow | null>(DEMO_WORKFLOW);
  const [approvals, setApprovals] = useState<Approval[]>(DEMO_APPROVALS);
  const [refDocs, setRefDocs] = useState<RefDoc[]>(DEMO_REFERENCE_DOCS);
  const [logs, setLogs] = useState<LogEntry[]>(DEMO_LOGS);
  const [historyEvents, setHistoryEvents] = useState<AuditEntry[]>([]);
  const [versions] = useState<VersionEntry[]>(DEMO_VERSIONS);
  const [reviewCount, setReviewCount] = useState(
    DEMO_DISPO_COMMENTS.length,
  );
  const [showPhaseDialog, setShowPhaseDialog] = useState(false);
  const [pendingPhase, setPendingPhase] = useState<string | null>(null);

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
    () => workflow?.steps?.map((s) => ({ id: s.name, label: s.name })) ?? [],
    [workflow?.steps],
  );

  const phaseCounts = useMemo(() => {
    const map: Record<string, number> = {};
    approvals.forEach((a) => {
      if (a.phaseId) map[a.phaseId] = (map[a.phaseId] || 0) + 1;
    });
    return map;
  }, [approvals]);

  // ▼ data hooks
  const { data: projectData, isLoading: projectLoading } = useProject(id as string);
  const { data: workflowData, isLoading: phasesLoading } = usePhases(projectData?.workflow);
  const {
    approvals: approvalsData,
    approve,
    reset,
    remind,
    isLoading: approvalsLoading,
  } = useApprovals({ workflow: projectData?.workflow, phase: projectData?.currentPhaseId });
  const { data: reviewCountData, isLoading: reviewLoading } = useReviewSummary(
    projectData?.id,
    projectData?.currentPhaseId,
  );

  useEffect(() => {
    // If this is the demo project ID, always use demo data
    if (id === DEMO_PROJECT.id) {
      setProject(DEMO_PROJECT);
    } else {
      setProject(projectData ?? null);
    }
  }, [projectData, id]);
  useEffect(() => {
    // If this is the demo project ID, always use demo workflow
    if (id === DEMO_PROJECT.id) {
      setWorkflow(DEMO_WORKFLOW);
    } else {
      setWorkflow(workflowData ?? null);
    }
  }, [workflowData, id]);
  useEffect(() => {
    // If this is the demo project ID, always use demo approvals
    if (id === DEMO_PROJECT.id) {
      setApprovals(DEMO_APPROVALS);
    } else {
      setApprovals(approvalsData ?? []);
    }
  }, [approvalsData, id]);
  useEffect(() => {
    // If this is the demo project ID, always use demo review count
    if (id === DEMO_PROJECT.id) {
      setReviewCount(DEMO_DISPO_COMMENTS.length);
    } else {
      setReviewCount(reviewCountData?.count ?? 0);
    }
  }, [reviewCountData, id]);

  useEffect(() => {
    if (!id || !username) {
      setLogs(DEMO_LOGS);
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
      .catch(() => setLogs(DEMO_LOGS));
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
      setPendingPhase(phaseId);
      setShowPhaseDialog(true);
    },
    [project?.currentPhaseId],
  );

  const confirmPhaseChange = useCallback(() => {
    if (pendingPhase) {
      handlePhaseChange(pendingPhase);
    }
    setShowPhaseDialog(false);
    setPendingPhase(null);
  }, [pendingPhase, handlePhaseChange]);

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
      .catch(() => setHistoryEvents(DEMO_APPROVAL_HISTORY))
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
      if (sigId) {
        router.push(
          `/documenso/${encodeURIComponent(String(sigId))}?return=${encodeURIComponent(`/projects/${id}#approvals`)}&approval=${encodeURIComponent(aid)}`,
        );
      }
    } catch {
      /* handled in hook */
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

  // ▼ save optimistic / autosave placeholder (debounce)
  const autosave = useCallback(() => {
    console.info("autosave stub");
  }, []);
  useEffect(() => {
    const id = setTimeout(autosave, 1500);
    return () => clearTimeout(id);
  }, [approvals, autosave]);

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
                <CardTitle>Workflow</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="flex items-center gap-2 text-sm">
                  {workflow?.steps?.map((s, i) => (
                    <li key={s.name} className="flex items-center gap-1">
                      <span
                        className={cn(
                          "w-6 h-6 flex items-center justify-center rounded-full border text-xs font-semibold",
                          s.status === "complete" &&
                            "bg-green-500 border-green-500 text-white",
                          s.status === "active" &&
                            "bg-blue-500 border-blue-500 text-white animate-pulse",
                          s.status === "pending" &&
                            "bg-gray-200 dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-400",
                        )}
                      >
                        {i + 1}
                      </span>
                      <span>{s.name}</span>
                      {i < workflow.steps!.length - 1 && (
                        <span className="mx-1 text-gray-400">→</span>
                      )}
                    </li>
                  ))}
                </ol>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
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

        {/* APPROVALS SECTION */}
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
            <CardContent className="overflow-x-auto">
              <ApprovalTable
                approvals={approvalsForPhase}
                currentUser={username}
                canEdit={canEdit}
                onSign={signApproval}
                onReset={resetApprovalLocal}
                onRemove={(id) =>
                  setApprovals((prev) => prev.filter((x) => x.id !== id))
                }
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
                <Link href={`/projects/${id}/reviews`}>
                  Open review workspace
                </Link>
              </Button>
            </CardContent>
          </Card>
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
          <AuditTimeline events={historyEvents.length ? historyEvents : DEMO_APPROVAL_HISTORY} />
        </DialogContent>
      </Dialog>
    </>
  );
}
