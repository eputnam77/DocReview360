import React, { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Users2,
  CheckCircle2,
  Clock,
  BarChart2,
  FileEdit,
  Mail,
  Trash,
  PlusCircle,
  Eye,
  Download,
  Check,
  X,
  RotateCcw,
  MoreHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import UploadDropzone from "@/components/workflow/UploadDropzone";
import { Menu, Transition } from "@headlessui/react";

/**
 * Types -------------------------------------------------------------------
 */
interface Project {
  id: string;
  number: string | number;
  type: string;
  title: string;
  status: string;
  progress: number;
  updated?: string;
  user?: string;
  editor?: "tiptap" | "toast" | "codex" | "word";
}
interface LogEntry {
  timestamp: string;
  action: string;
  metadata?: Record<string, any>;
}
interface Workflow {
  id: string;
  phase: string;
  steps?: { name: string; status: "complete" | "active" | "pending" }[];
}
interface Approval {
  id: string;
  reviewer: string;
  email: string;
  state: "pending" | "approved" | "overdue" | "rejected" | string;
  statusDate: string;
  signedAt?: string;
  comments?: string;
  documensoSigId?: string;
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
}
interface RefDoc {
  name: string;
  url: string;
  type: string;
  file?: File;
}

/**
 * Demo data (replace with API calls) --------------------------------------
 */
const DEMO_PROJECT: Project = {
  id: "123e-ac-101",
  number: "AC 20-197",
  type: "Advisory Circular",
  title: "Turbine Engine and Airframe Sensor Icing Compliance",
  status: "In Progress",
  progress: 40,
  updated: "2025-07-04",
  user: "Jane Doe",
  editor: "tiptap",
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
    statusDate: "2025-07-04",
    documensoSigId: "sig-123",
    comments: "Please check the legal cites.",
  },
  {
    id: "appr-2",
    reviewer: "John Smith",
    email: "john@example.com",
    state: "approved",
    statusDate: "2025-07-05",
    signedAt: "2025-07-05T14:30:00Z",
    comments: "Approved, no changes needed.",
  },
  {
    id: "appr-3",
    reviewer: "Jill Admin",
    email: "jill@example.com",
    state: "overdue",
    statusDate: "2025-07-06",
    comments: "",
  },
];
const DEMO_LOGS: LogEntry[] = [
  { timestamp: "2025-07-04", action: "Draft created" },
  { timestamp: "2025-07-04", action: "Initial review started" },
  { timestamp: "2025-07-05", action: "Draft updated" },
];
const DEMO_DISPO_COMMENTS: DispoComment[] = [
  {
    id: "c1",
    reviewer: "Jane Doe",
    routing: "Legal",
    email: "jane@example.com",
    pagePara: "2/3.1",
    comment: "Clarify regulatory reference.",
    change: "Rewrite as: 'per 14 CFR 21.8...'",
    disposition: "Accepted",
  },
  {
    id: "c2",
    reviewer: "John Smith",
    routing: "Tech",
    email: "john@example.com",
    pagePara: "5/6.2",
    comment: "Consider splitting into two paragraphs.",
    change: "Break up 6.2 for clarity.",
    disposition: "Deferred",
  },
];
const DEMO_REFERENCE_DOCS: RefDoc[] = [
  {
    name: "Requirements.pdf",
    url: "https://file-examples.com/wp-content/uploads/2017/10/file-sample_150kB.pdf",
    type: "pdf",
  },
  {
    name: "Draft_v1.docx",
    url: "https://file-examples.com/wp-content/uploads/2017/02/file-sample_100kB.docx",
    type: "docx",
  },
];

/**
 * Utility helpers ---------------------------------------------------------
 */
function slugify(str: string) {
  return str.toLowerCase().replace(/\s+/g, "");
}

function ProgBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-3">
      <div
        className={cn(
          "h-3 rounded-full transition-all",
          pct === 100
            ? "bg-green-500"
            : pct >= 70
            ? "bg-blue-500"
            : pct > 0
            ? "bg-yellow-400"
            : "bg-gray-400"
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) {
  return (
    <Card className="shadow-sm">
      <CardContent className="flex items-center gap-4 p-4">
        <Icon className={cn("w-7 h-7", color)} />
        <div>
          <p className="text-base font-bold leading-none">{value}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function WorkflowStepper({ steps }: { steps?: Workflow["steps"] }) {
  if (!steps?.length) return null;
  return (
    <ol className="flex items-center gap-0.5 text-sm">
      {steps.map((s, idx) => (
        <li key={s.name} className="flex items-center gap-0.5">
          <span
            className={cn(
              "w-6 h-6 flex items-center justify-center rounded-full border text-xs font-semibold",
              s.status === "complete" && "bg-green-500 border-green-500 text-white",
              s.status === "active" && "bg-blue-500 border-blue-500 text-white animate-pulse",
              s.status === "pending" && "bg-gray-200 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300"
            )}
          >
            {idx + 1}
          </span>
          <span className="ml-1 mr-3 whitespace-nowrap">{s.name}</span>
        </li>
      ))}
    </ol>
  );
}

/**
 * 3‑dot menu component for row actions ------------------------------------
 */
function RowMenu({ children }: { children: React.ReactNode }) {
  return (
    <Menu as="div" className="relative inline-block text-left">
      <Menu.Button className="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <MoreHorizontal className="w-4 h-4" />
      </Menu.Button>
      <Transition
        enter="transition duration-100 ease-out"
        enterFrom="transform scale-95 opacity-0"
        enterTo="transform scale-100 opacity-100"
        leave="transition duration-75 ease-out"
        leaveFrom="transform scale-100 opacity-100"
        leaveTo="transform scale-95 opacity-0"
      >
        <Menu.Items className="absolute z-10 right-0 mt-2 w-44 origin-top-right rounded-md bg-white dark:bg-gray-900 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          {children}
        </Menu.Items>
      </Transition>
    </Menu>
  );
}

/**
 * Sticky section nav -------------------------------------------------------
 */
const sections = [
  { id: "details", label: "Details" },
  { id: "approvals", label: "Approvals" },
  { id: "comments", label: "Comments" },
  { id: "history", label: "History" },
];
function StickyNav() {
  return (
    <nav className="sticky top-0 z-20 bg-white/80 dark:bg-gray-900/80 backdrop-blur border-b border-gray-200 dark:border-gray-700">
      <ul className="flex gap-4 px-8 py-2 text-sm font-medium overflow-x-auto">
        {sections.map((s) => (
          <li key={s.id}>
            <a href={`#${s.id}`} className="text-gray-600 dark:text-gray-300 hover:text-indigo-600">
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/**
 * Bulk action bar ----------------------------------------------------------
 */
function BulkBar({ count, onEmail }: { count: number; onEmail: () => void }) {
  if (count === 0) return null;
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 shadow-lg rounded-full px-4 py-2 flex items-center gap-4">
      <span className="text-sm font-medium">{count} selected</span>
      <Button size="sm" onClick={onEmail}>
        <Mail className="w-4 h-4 mr-1" /> Email selected
      </Button>
    </div>
  );
}

/**
 * -------------------------------------------------------------------------
 * Main page
 * -------------------------------------------------------------------------
 */
export default function ProjectDetailsPage() {
  const router = useRouter();
  const { id } = router.query;

  // state ------------------------------------------------------------------
  const [project, setProject] = useState<Project | null>(null);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [referenceDocs, setReferenceDocs] = useState<RefDoc[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [dispoComments, setDispoComments] = useState<DispoComment[]>([]);
  const [loading, setLoading] = useState(true);

  // fetch demo -------------------------------------------------------------
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setTimeout(() => {
      setProject(DEMO_PROJECT);
      setWorkflow(DEMO_WORKFLOW);
      setApprovals(DEMO_APPROVALS);
      setReferenceDocs(DEMO_REFERENCE_DOCS);
      setDispoComments(DEMO_DISPO_COMMENTS);
      setLogs(DEMO_LOGS);
      setLoading(false);
    }, 300);
  }, [id]);

  // memo helpers -----------------------------------------------------------
  const reviewStats = useMemo(() => {
    const assigned = approvals.length;
    const approved = approvals.filter((a) => a.state === "approved").length;
    const pending = approvals.filter((a) => a.state === "pending").length;
    const overdue = approvals.filter((a) => a.state === "overdue").length;
    return { assigned, approved, pending, overdue };
  }, [approvals]);

  const editor = project?.editor ?? "tiptap";
  const editDocUrl = `/editors/${editor}?projectId=${id}&returnTo=/projects/${id}`;

  // bulk email handler -----------------------------------------------------
  const handleBulkEmail = () => {
    const emails = approvals.filter((a) => selected.includes(a.id)).map((a) => a.email);
    alert(`Would send bulk email to: ${emails.join(", ")}`);
  };

  // ui mutation helpers (kept minimal for brevity) -------------------------
  const toggleSelect = (id: string) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  if (loading) return <p className="p-4">Loading…</p>;
  if (!project) return <p className="p-4">Project not found.</p>;

  return (
    <>
      {/* sticky nav */}
      <StickyNav />

      <div className="p-8 space-y-10">
        {/* header summary (sticky) */}
        <div className="sticky top-12 z-10 bg-white/90 dark:bg-gray-900/90 backdrop-blur border-b border-gray-200 dark:border-gray-700 py-2 px-4 flex items-center justify-between">
          <div className="space-x-2 text-sm text-gray-600 dark:text-gray-300">
            <span className="font-mono">{project.number}</span>
            <span>•</span>
            <span>{project.title}</span>
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300">
              {project.status}
            </span>
          </div>
          <div className="w-40"><ProgBar value={project.progress} /></div>
        </div>

        {/* ---------------------------------------------------------------- */}
        <section id="details" className="space-y-8">
          <Card className="max-w-full overflow-x-auto">
            <CardHeader>
              <CardTitle>Project Details</CardTitle>
            </CardHeader>
            <CardContent>
              <Table className="min-w-[600px] text-sm">
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>#</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-mono">{project.id}</TableCell>
                    <TableCell>{project.number}</TableCell>
                    <TableCell>{project.type}</TableCell>
                    <TableCell>{project.title}</TableCell>
                    <TableCell>{project.status}</TableCell>
                    <TableCell>{project.updated}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
            <StatCard icon={Users2} label="Assigned" value={reviewStats.assigned} color="text-indigo-600" />
            <StatCard icon={CheckCircle2} label="Approved" value={reviewStats.approved} color="text-emerald-600" />
            <StatCard icon={Clock} label="Pending" value={reviewStats.pending} color="text-orange-600" />
            <StatCard icon={BarChart2} label="Overdue" value={reviewStats.overdue} color="text-red-600" />
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Workflow</CardTitle>
              </CardHeader>
              <CardContent>
                <WorkflowStepper steps={workflow?.steps} />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Current phase: {workflow?.phase}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Overall Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <ProgBar value={project.progress} />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">{project.progress}% complete</p>
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-center">
            <Button asChild className="text-lg px-6 py-3 rounded-lg shadow-lg">
              <Link href={editDocUrl}>
                <FileEdit className="w-5 h-5 mr-2" />
                {editor === "word" ? "View" : "Edit"} Document
              </Link>
            </Button>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        <section id="approvals" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Approvals</CardTitle>
            </CardHeader>
            <CardContent>
              <Table className="overflow-x-auto">
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <input
                        type="checkbox"
                        aria-label="Select all reviewers"
                        checked={selected.length === approvals.length && approvals.length > 0}
                        onChange={(e) =>
                          setSelected(e.target.checked ? approvals.map((a) => a.id) : [])
                        }
                      />
                    </TableHead>
                    <TableHead>Reviewer</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Comments</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {approvals.map((a) => (
                    <TableRow key={a.id} className="group">
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selected.includes(a.id)}
                          onChange={() => toggleSelect(a.id)}
                          aria-label={`Select ${a.reviewer}`}
                        />
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{a.reviewer}</TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-xs font-semibold capitalize",
                            {
                              approved: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
                              pending: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
                              overdue: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
                              rejected: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
                            }[a.state as keyof typeof a]
                          )}
                        >
                          {a.state}
                        </span>
                      </TableCell>
                      <TableCell>{a.statusDate}</TableCell>
                      <TableCell className="max-w-xs truncate text-sm text-gray-600 dark:text-gray-400">
                        {a.comments || "—"}
                      </TableCell>
                      <TableCell className="text-right min-w-[60px]">
                        <RowMenu>
                          <Menu.Item>
                            {({ active }) => (
                              <button
                                className={cn(
                                  "w-full px-3 py-2 text-left text-sm",
                                  active && "bg-indigo-50 dark:bg-gray-800"
                                )}
                                onClick={() => alert("Sign/approve")}
                              >
                                <Check className="w-4 h-4 mr-2 inline" /> Sign / Approve
                              </button>
                            )}
                          </Menu.Item>
                          <Menu.Item>
                            {({ active }) => (
                              <button
                                className={cn(
                                  "w-full px-3 py-2 text-left text-sm",
                                  active && "bg-indigo-50 dark:bg-gray-800"
                                )}
                                onClick={() => alert("Send email")}
                              >
                                <Mail className="w-4 h-4 mr-2 inline" /> Send Email
                              </button>
                            )}
                          </Menu.Item>
                          <Menu.Item>
                            {({ active }) => (
                              <button
                                className={cn(
                                  "w-full px-3 py-2 text-left text-sm text-red-600",
                                  active && "bg-indigo-50 dark:bg-gray-800"
                                )}
                                onClick={() => alert("Remove reviewer")}
                              >
                                <Trash className="w-4 h-4 mr-2 inline" /> Remove
                              </button>
                            )}
                          </Menu.Item>
                        </RowMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </section>

        {/* bulk bar */}
        <BulkBar count={selected.length} onEmail={handleBulkEmail} />

        {/* ---------------------------------------------------------------- */}
        <section id="comments" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Comments & Disposition</CardTitle>
            </CardHeader>
            <CardContent>
              <Table className="text-sm overflow-x-auto">
                <TableHeader>
                  <TableRow>
                    <TableHead>Reviewer</TableHead>
                    <TableHead>Routing</TableHead>
                    <TableHead>Page/Para</TableHead>
                    <TableHead>Comment</TableHead>
                    <TableHead>Change</TableHead>
                    <TableHead>Disposition</TableHead>
                    <TableHead className="min-w-[60px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dispoComments.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell>{c.reviewer}</TableCell>
                      <TableCell>{c.routing}</TableCell>
                      <TableCell>{c.pagePara}</TableCell>
                      <TableCell className="max-w-xs truncate">{c.comment}</TableCell>
                      <TableCell className="max-w-xs truncate">{c.change}</TableCell>
                      <TableCell>{c.disposition}</TableCell>
                      <TableCell className="text-right">
                        <RowMenu>
                          <Menu.Item>
                            {({ active }) => (
                              <button
                                className={cn(
                                  "w-full px-3 py-2 text-left text-sm",
                                  active && "bg-indigo-50 dark:bg-gray-800"
                                )}
                                onClick={() => alert("Edit comment")}
                              >
                                <FileEdit className="w-4 h-4 mr-2 inline" /> Edit
                              </button>
                            )}
                          </Menu.Item>
                          <Menu.Item>
                            {({ active }) => (
                              <button
                                className={cn(
                                  "w-full px-3 py-2 text-left text-sm text-red-600",
                                  active && "bg-indigo-50 dark:bg-gray-800"
                                )}
                                onClick={() => alert("Delete comment")}
                              >
                                <Trash className="w-4 h-4 mr-2 inline" /> Delete
                              </button>
                            )}
                          </Menu.Item>
                        </RowMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </section>

        {/* ---------------------------------------------------------------- */}
        <section id="history" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Audit History</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-5 text-sm space-y-1">
                {logs.map((l, i) => (
                  <li key={i}>
                    {l.timestamp} – {l.action}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </section>
      </div>
    </>
  );
}
