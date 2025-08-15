// frontend/pages/projects/[id]/index.tsx
"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { API } from "@/lib/api";
import PhaseTabs from "@/components/PhaseTabs";
import { cn } from "@/lib/utils";
import { useUserStore } from "@/state/user";
import { Disclosure, Menu, Transition } from "@headlessui/react";
import {
    BarChart2,
    Check,
    CheckCircle2,
    Clock,
    Download,
    FileEdit,
    History,
    LayoutList,
    Mail,
    MoreHorizontal,
    Trash,
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
  timestamp: string;
  action: string;
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
  statusDate: string;
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

// Row action menu
function RowMenu({ children }: { children: React.ReactNode }) {
  return (
    <Menu as="div" className="relative inline-block text-left">
      <Menu.Button className="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring">
        <MoreHorizontal className="w-4 h-4" />
      </Menu.Button>
      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 z-20 mt-2 w-48 rounded-md bg-white dark:bg-gray-900 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          {children}
        </Menu.Items>
      </Transition>
    </Menu>
  );
}

// Sticky nav
const NAV = [
  { id: "details", label: "Details" },
  { id: "approvals", label: "Approvals" },
  { id: "reviews", label: "Reviews" },
  { id: "history", label: "History" },
];
function StickyNav() {
  return (
    <nav className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur supports-backdrop-blur:border-b supports-backdrop-blur:border-gray-200 dark:supports-backdrop-blur:border-gray-700">
      <ul className="flex gap-6 px-8 py-2 text-sm font-medium overflow-x-auto scrollbar-hide">
        {NAV.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              className="hover:text-indigo-600 dark:hover:text-indigo-400 text-gray-600 dark:text-gray-300"
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
      <DialogContent className="max-w-md sm:max-w-md">
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
  const [selected, setSelected] = useState<string[]>([]);
  const [refDocs, setRefDocs] = useState<RefDoc[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [versions] = useState<VersionEntry[]>([]);
  const [reviewCount, setReviewCount] = useState(0);

  const approvalsForPhase = useMemo(
    () =>
      approvals.filter(
        (a) => !project?.currentPhaseId || a.phaseId === project.currentPhaseId,
      ),
    [approvals, project?.currentPhaseId],
  );

  const [loading, setLoading] = useState(true);
  const [showVersions, setShowVersions] = useState(false);

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

  // ▼ fetch data from API
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    console.log('Fetching project data from:', `${API}/projects/${id}`);
    fetch(`${API}/projects/${id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(async (proj) => {
        // Map backend data to frontend interface
        const mappedProject: Project = {
          id: proj.id,
          number: proj.number || 1,
          type: proj.doc_type || "Unknown",
          title: proj.name || "Untitled",
          owner: proj.user || "Unknown",
          status: proj.status || "Draft",
          progress: proj.progress || 0, // Use backend progress if available
          updated: proj.updated || proj.created || new Date().toISOString().split('T')[0],
          editor: "tiptap", // Default editor
          currentPhaseId: proj.current_phase_id || proj.phase || null,
        };
        setProject(mappedProject);
        
        // Load workflow and approvals if project has a workflow
        if (proj.workflow) {
          console.log('Project has workflow:', proj.workflow);
          
          // Fetch workflow details
          try {
            const wfRes = await fetch(`${API}/workflows/${proj.workflow}`);
            if (wfRes.ok) {
              const workflowData = await wfRes.json();
              console.log('Workflow data:', workflowData);
              setWorkflow(workflowData);
            }
          } catch (error) {
            console.error('Error fetching workflow:', error);
          }
          
          // Fetch approvals for this workflow
          try {
            const phaseParam = mappedProject.currentPhaseId
              ? `&phase=${encodeURIComponent(mappedProject.currentPhaseId)}`
              : "";
            const apRes = await fetch(
              `${API}/approvals?workflow=${proj.workflow}${phaseParam}`,
            );
            if (apRes.ok) {
              const approvalsData = await apRes.json();
              console.log('Approvals data:', approvalsData);
              // Map backend approval data to frontend interface
              const mappedApprovals = approvalsData.map((approval: any) => ({
                id: approval.id,
                reviewer: approval.reviewer,
                email: approval.reviewer, // Use reviewer as email since backend doesn't have separate email field
                state: approval.state,
                statusDate:
                  approval.due_at || new Date().toISOString().split('T')[0],
                signedAt: approval.signed_at,
                comments: approval.comments || '',
                documensoSigId: approval.signature,
                description: approval.description, // Add description from backend
                phaseId: approval.phase_id,
                required: approval.required,
              }));
              setApprovals(mappedApprovals);
            }
          } catch (error) {
            console.error('Error fetching approvals:', error);
            setApprovals([]); // Set empty array on error
          }

          // Fetch review summary for current phase
          try {
            const revPhase = mappedProject.currentPhaseId
              ? `?phase=${encodeURIComponent(mappedProject.currentPhaseId)}`
              : "";
            const revRes = await fetch(
              `${API}/projects/${proj.id}/reviews${revPhase}`,
            );
            if (revRes.ok) {
              const reviewsData = await revRes.json();
              setReviewCount(Array.isArray(reviewsData) ? reviewsData.length : 0);
            } else {
              setReviewCount(0);
            }
          } catch (error) {
            console.error('Error fetching reviews:', error);
            setReviewCount(0);
          }
        } else {
          console.log('Project has no workflow');
          setWorkflow(null);
          setApprovals([]);
          setReviewCount(0);
        }
        
        // Set other data (placeholder until API provides it)
        setDispos([]);
        setRefDocs([]);
        setLogs([]);
      })
      .catch((error) => {
        console.error('API call failed:', error);
        setProject(null);
        setWorkflow(null);
        setApprovals([]);
        setDispos([]);
        setRefDocs([]);
        setLogs([]);
      })
      .finally(() => setLoading(false));
  }, [id]);

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

  const toggleSelect = (aid: string) =>
    setSelected((prev) =>
      prev.includes(aid) ? prev.filter((x) => x !== aid) : [...prev, aid],
    );

  const sendReminder = () => {
    const emails = approvalsForPhase
      .filter((a) => a.state === "pending" || a.state === "overdue")
      .map((a) => a.email);
    alert("Reminder sent to: " + emails.join(", "));
  };

  const signApproval = (aid: string) => {
    const existing = approvals.find((a) => a.id === aid);
    if (existing?.state === "approved") {
      alert("Approval already completed.");
      return;
    }

    console.log(`Starting signature process for approval ${aid}`);

    // Show loading state
    setApprovals((prev) =>
      prev.map((a) =>
        a.id === aid ? { ...a, state: "pending" as const } : a,
      ),
    );

    fetch(`${API}/approvals/${aid}/sign`, {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
      }
    })
      .then((r) => {
        console.log(`Signature request response: ${r.status} ${r.statusText}`);
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        }
        return r.json();
      })
      .then((d) => {
        console.log(`Signature request successful:`, d);
        // Prefer local Documenso page route over external URL
        const sigId = d?.id ?? d?.signature?.id;
        if (!sigId) {
          throw new Error("Missing signature id in response");
        }

        // Update local state with signature ID
        setApprovals((prev) =>
          prev.map((a) =>
            a.id === aid ? { ...a, documensoSigId: sigId } : a,
          ),
        );

        // Redirect to our internal Documenso page
        const internalUrl = `/documenso/${encodeURIComponent(String(sigId))}?return=${encodeURIComponent(`/projects/${id}#approvals`)}&approval=${encodeURIComponent(aid)}`;
        console.log(`Redirecting to: ${internalUrl}`);
        router.push(internalUrl);
      })
      .catch((error) => {
        console.error("Signature request failed:", error);
        alert(`Failed to start signing: ${error.message}`);

        // Reset approval state on error
        setApprovals((prev) =>
          prev.map((a) =>
            a.id === aid ? { ...a, state: "pending" as const } : a,
          ),
        );
      });
  };

  const resetApprovalLocal = (aid: string) => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(`approval-${aid}`);
    }
    setApprovals((prev) =>
      prev.map((a) =>
        a.id === aid
          ? { ...a, state: "pending", signedAt: undefined, documensoSigId: undefined }
          : a,
      ),
    );
  };

  const syncApprovalWithBackend = async (approvalId: string, signatureId: string) => {
    try {
      const response = await fetch(`${API}/approvals/${approvalId}`, {
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
      alert(
        "Escalation: overdue approvals - " +
          overdue.map((o) => o.reviewer).join(", "),
      );
    }
  }, [approvalsForPhase, isOwner]);

  if (loading) return <p className="p-4">Loading…</p>;
  if (!project) return <p className="p-4">Project not found.</p>;

  const editorURL = `/editors/${project.editor ?? "tiptap"}?projectId=${project.id}`;

  // ------------------------------------------------------------------------
  //                             RENDER
  // ------------------------------------------------------------------------
  return (
    <>
      <StickyNav />
      <div className="p-8 space-y-10">
        {/* Sticky summary bar */}
        <div className="sticky top-12 z-20 bg-white/90 dark:bg-gray-900/90 backdrop-blur border-b border-gray-200 dark:border-gray-700 py-2 px-4 flex items-center justify-between gap-4">
          <div className="truncate text-sm text-gray-600 dark:text-gray-300 space-x-2">
            <span className="font-mono">{project.number}</span>
            <span>•</span>
            <span className="truncate">{project.title}</span>
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300">
              {project.status}
            </span>
            <span className="hidden md:inline ml-4">Accountable: {project.owner}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-36 shrink-0">
              <ProgBar value={project.progress} />
            </div>
            <PhaseTabs
              phases={phaseList}
              activePhaseId={project.currentPhaseId || workflow?.phase}
              counts={phaseCounts}
              onChange={isOwner ? handlePhaseChange : undefined}
            />
            {isOwner && (
              <Button size="sm" onClick={exportRaci}>
                <Download className="w-4 h-4 mr-1" /> RACI CSV
              </Button>
            )}
            <Button
              size="icon"
              variant="ghost"
              title="Version timeline"
              onClick={() => setShowVersions(true)}
            >
              <History className="w-5 h-5" />
            </Button>
          </div>
        </div>

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
                      <Table className="min-w-[600px] text-sm">
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

          {/* KPI cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
            {[
              {
                icon: Users2,
                label: "Assigned",
                val: stats.assigned,
                col: "text-indigo-600",
              },
              {
                icon: CheckCircle2,
                label: "Approved",
                val: stats.approved,
                col: "text-emerald-600",
              },
              {
                icon: Clock,
                label: "Pending",
                val: stats.pending,
                col: "text-orange-600",
              },
              {
                icon: BarChart2,
                label: "Overdue",
                val: stats.overdue,
                col: "text-red-600",
              },
            ].map((s) => (
              <Card key={s.label} className="shadow-sm">
                <CardContent className="flex items-center gap-4 p-4">
                  <s.icon className={cn("w-7 h-7", s.col)} />
                  <div>
                    <p className="text-base font-bold leading-none">{s.val}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {s.label}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

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
              <Button size="sm" onClick={sendReminder}>
                <Mail className="w-4 h-4 mr-1" /> Remind Pending
              </Button>
            )}
          </div>
          <Card>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <input
                        type="checkbox"
                        aria-label="Select all"
                        checked={
                          selected.length === approvalsForPhase.length &&
                          approvalsForPhase.length > 0
                        }
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? approvalsForPhase.map((a) => a.id)
                              : [],
                          )
                        }
                      />
                    </TableHead>
                    <TableHead>Reviewer</TableHead>
                    <TableHead>Role/Description</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Signed At</TableHead>
                    <TableHead>Comments</TableHead>
                    {canEdit && <TableHead />}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {approvalsForPhase.length > 0 ? (
                    approvalsForPhase.map((a) => (
                      <TableRow key={a.id} className="group">
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selected.includes(a.id)}
                            onChange={() => toggleSelect(a.id)}
                          />
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {a.reviewer}
                        </TableCell>
                        <TableCell className="max-w-xs truncate text-sm text-gray-600 dark:text-gray-400">
                          {a.description || "—"}
                        </TableCell>
                        <TableCell>
                          <span
                            className={classNames(
                              "px-2 py-0.5 rounded-full text-xs font-semibold capitalize",
                              a.state === "approved" &&
                                "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
                              a.state === "pending" &&
                                "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
                              a.state === "overdue" &&
                                "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
                              a.state === "rejected" &&
                                "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
                            )}
                          >
                            {a.state}
                          </span>
                        </TableCell>
                        <TableCell>
                          {a.signedAt
                            ? new Date(a.signedAt).toLocaleString()
                            : "—"}
                        </TableCell>
                        <TableCell className="max-w-xs truncate text-sm text-gray-600 dark:text-gray-400">
                          {a.comments || "—"}
                        </TableCell>
                        {canEdit && (
                          <TableCell className="text-right">
                            <RowMenu>
                              <Menu.Item as={Fragment}>
                                {({ active, close }) => (
                                  <button
                                    className={classNames(
                                      "w-full px-3 py-2 text-left text-sm",
                                      active && "bg-indigo-50 dark:bg-gray-800",
                                    )}
                                    onClick={() => {
                                      close();
                                      signApproval(a.id);
                                    }}
                                  >
                                    {" "}
                                    <Check className="w-4 h-4 inline mr-2" /> Sign
                                    / Approve
                                  </button>
                                )}
                              </Menu.Item>
                              <Menu.Item>
                                {({ active }) => (
                                  <button
                                    className={classNames(
                                      "w-full px-3 py-2 text-left text-sm",
                                      active && "bg-indigo-50 dark:bg-gray-800",
                                    )}
                                    onClick={() => resetApprovalLocal(a.id)}
                                  >
                                    {" "}
                                    <RotateCcw className="w-4 h-4 inline mr-2" />
                                    Reset
                                  </button>
                                )}
                              </Menu.Item>
                              <Menu.Item>
                                {({ active }) => (
                                  <button
                                    className={classNames(
                                      "w-full px-3 py-2 text-left text-sm",
                                      active && "bg-indigo-50 dark:bg-gray-800",
                                    )}
                                    onClick={() => alert("Email")}
                                  >
                                    {" "}
                                    <Mail className="w-4 h-4 inline mr-2" /> Send
                                    email
                                  </button>
                                )}
                              </Menu.Item>
                              <Menu.Item>
                                {({ active }) => (
                                  <button
                                    className={classNames(
                                      "w-full px-3 py-2 text-left text-sm text-red-600",
                                      active && "bg-indigo-50 dark:bg-gray-800",
                                    )}
                                    onClick={() =>
                                      setApprovals(
                                        approvals.filter((x) => x.id !== a.id),
                                      )
                                    }
                                  >
                                    {" "}
                                    <Trash className="w-4 h-4 inline mr-2" />{" "}
                                    Remove
                                  </button>
                                )}
                              </Menu.Item>
                            </RowMenu>
                          </TableCell>
                        )}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={canEdit ? 6 : 5} className="text-center py-8">
                        <div className="text-gray-500 dark:text-gray-400">
                          <Users2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p className="text-sm font-medium">No approvals configured</p>
                          <p className="text-xs mt-1">
                            {workflow ? 
                              `This project uses the "${workflow.phase}" workflow. Approvals will appear here once they are added.` :
                              "This project has no workflow configured. Add a workflow to enable approvals."
                            }
                          </p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
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
                  <Card>
                    <CardContent>
                      <ul className="list-disc pl-5 text-sm space-y-1">
                        {logs.map((l, i) => (
                          <li key={i}>
                            {l.timestamp} — {l.action}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </Transition>
              </>
            )}
          </Disclosure>
        </section>
      </div>

      {/* Modals */}
      <VersionDrawer
        open={showVersions}
        onClose={() => setShowVersions(false)}
        versions={versions}
      />
    </>
  );
}
