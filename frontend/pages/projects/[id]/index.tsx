import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Users2, CheckCircle2, Clock, BarChart2, FileEdit, Mail, Trash, PlusCircle } from "lucide-react";
import { cn } from "@/lib/utils";

// --- Types ---
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
  steps?: { name: string; status: string; }[];
}
interface Approval {
  id: string;
  reviewer: string;
  email: string;
  state: "pending" | "approved" | "overdue" | string;
  statusDate: string;
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

// --- Demo Data ---
const DEMO_PROJECT: Project = {
  id: "123e-ac-101",
  number: "AC-101",
  type: "Advisory Circular",
  title: "Policy Update",
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
  { id: "appr-1", reviewer: "Jane Doe", email: "jane@example.com", state: "pending", statusDate: "2025-07-04", documensoSigId: "sig-123", comments: "Please check the legal cites." },
  { id: "appr-2", reviewer: "John Smith", email: "john@example.com", state: "approved", statusDate: "2025-07-05", comments: "Approved, no changes needed." },
  { id: "appr-3", reviewer: "Jill Admin", email: "jill@example.com", state: "overdue", statusDate: "2025-07-06", comments: "" },
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
    disposition: "Accepted"
  },
  {
    id: "c2",
    reviewer: "John Smith",
    routing: "Tech",
    email: "john@example.com",
    pagePara: "5/6.2",
    comment: "Consider splitting into two paragraphs.",
    change: "Break up 6.2 for clarity.",
    disposition: "Deferred"
  },
];

// --- UI Helpers ---
function StatCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: number; color?: string }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <Icon className={`w-7 h-7 ${color || "text-indigo-600"}`} />
        <div>
          <p className="text-lg font-bold leading-none">{value}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value || 0));
  const status =
    pct === 100
      ? "bg-green-500"
      : pct >= 70
      ? "bg-blue-500"
      : pct > 0
      ? "bg-yellow-400"
      : "bg-gray-300";
  return (
    <div className="w-full bg-gray-200 rounded-full h-3">
      <div
        className={cn(
          "h-3 rounded-full transition-all duration-200",
          status
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function WorkflowSteps({ steps }: { steps: Workflow["steps"] }) {
  return (
    <div className="flex items-center gap-3 my-2">
      {steps?.map((step, idx) => (
        <span key={step.name} className={cn(
          "px-2 py-1 rounded text-xs font-medium",
          step.status === "complete"
            ? "bg-green-100 text-green-800"
            : step.status === "active"
            ? "bg-blue-100 text-blue-800"
            : "bg-gray-100 text-gray-700"
        )}>
          {step.name}
          {idx < (steps.length - 1) && <span className="mx-2 text-gray-400">→</span>}
        </span>
      ))}
    </div>
  );
}

// --- Main Page ---
export default function ProjectDetailsPage() {
  const router = useRouter();
  const { id } = router.query;
  const [project, setProject] = useState<Project | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [selectedApprovals, setSelectedApprovals] = useState<string[]>([]);
  const [showAddReviewer, setShowAddReviewer] = useState(false);
  const [newReviewer, setNewReviewer] = useState({ reviewer: "", email: "" });
  const [dispoComments, setDispoComments] = useState<DispoComment[]>([]);
  const [showAddComment, setShowAddComment] = useState(false);
  const [newComment, setNewComment] = useState<Omit<DispoComment, "id">>({
    reviewer: "",
    routing: "",
    email: "",
    pagePara: "",
    comment: "",
    change: "",
    disposition: "",
  });
  const [loading, setLoading] = useState(true);

  // Demo fetch logic
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setTimeout(() => {
      setProject(DEMO_PROJECT); // Replace with real fetch(`/api/projects/${id}`)
      setWorkflow(DEMO_WORKFLOW);
      setApprovals(DEMO_APPROVALS);
      setDispoComments(DEMO_DISPO_COMMENTS);
      setLogs(DEMO_LOGS);
      setLoading(false);
    }, 300);
  }, [id]);

  if (loading) return <p className="p-4">Loading…</p>;
  if (!project) return <p className="p-4">Project not found.</p>;

  const editor = project.editor ?? "tiptap";
  const editDocUrl = `/editors/${editor}?projectId=${id}&returnTo=/projects/${id}`;

  // Review KPI stats
  const assigned = approvals.length;
  const approved = approvals.filter(a => a.state === "approved").length;
  const pending = approvals.filter(a => a.state === "pending").length;
  const overdue = approvals.filter(a => a.state === "overdue").length;

  // Approval Table helpers
  const handleSelectApproval = (id: string, checked: boolean) => {
    setSelectedApprovals((prev) =>
      checked ? [...prev, id] : prev.filter((aid) => aid !== id)
    );
  };
  const handleSendEmail = (approval: Approval) => {
    // Integrate your real email send logic here.
    alert(`Email sent to ${approval.email} for review.`);
  };
  const handleRemoveReviewer = (id: string) => {
    setApprovals(approvals.filter((a) => a.id !== id));
    setSelectedApprovals((prev) => prev.filter((aid) => aid !== id));
  };
  const handleAddReviewer = () => {
    if (!newReviewer.reviewer || !newReviewer.email) return;
    setApprovals([
      ...approvals,
      {
        id: "appr-" + (Math.random() * 100000).toFixed(0),
        reviewer: newReviewer.reviewer,
        email: newReviewer.email,
        state: "pending",
        statusDate: new Date().toISOString().slice(0, 10),
        comments: "",
      },
    ]);
    setShowAddReviewer(false);
    setNewReviewer({ reviewer: "", email: "" });
  };

  // Disposition Comments helpers
  const handleRemoveComment = (id: string) => {
    setDispoComments(dispoComments.filter((c) => c.id !== id));
  };
  const handleAddComment = () => {
    setDispoComments([
      ...dispoComments,
      { ...newComment, id: "c" + (Math.random() * 100000).toFixed(0) },
    ]);
    setShowAddComment(false);
    setNewComment({
      reviewer: "",
      routing: "",
      email: "",
      pagePara: "",
      comment: "",
      change: "",
      disposition: "",
    });
  };

  return (
    <div className="p-8 space-y-8">

      {/* --- Project Details Table (horizontal) --- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            Project Details
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table className="min-w-full text-sm">
              <TableHeader>
                <TableRow>
                  <TableHead>Document Id</TableHead>
                  <TableHead>Document #</TableHead>
                  <TableHead>Document Type</TableHead>
                  <TableHead>Document Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-mono">{project.id}</TableCell>
                  <TableCell>{project.number}</TableCell>
                  <TableCell>{project.type}</TableCell>
                  <TableCell>{project.title}</TableCell>
                  <TableCell>
                    <span className={cn(
                      "px-2 py-1 rounded text-xs font-medium",
                      project.status === "Complete"
                        ? "bg-green-100 text-green-800"
                        : project.status === "In Progress"
                        ? "bg-blue-100 text-blue-800"
                        : project.status === "Draft"
                        ? "bg-yellow-100 text-yellow-800"
                        : project.status === "Overdue"
                        ? "bg-red-100 text-red-800"
                        : "bg-gray-100 text-gray-700"
                    )}>
                      {project.status}
                    </span>
                  </TableCell>
                  <TableCell>{project.updated?.slice(0, 10) ?? ""}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* --- Review Stats --- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl">
        <StatCard icon={Users2} label="Assigned" value={assigned} color="text-indigo-600" />
        <StatCard icon={CheckCircle2} label="Approved" value={approved} color="text-emerald-600" />
        <StatCard icon={Clock} label="Pending" value={pending} color="text-orange-600" />
        <StatCard icon={BarChart2} label="Overdue" value={overdue} color="text-red-600" />
      </div>

      {/* --- Workflow & Progress --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Workflow Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <WorkflowSteps steps={workflow?.steps} />
            <p className="text-xs text-gray-500 mt-1">Current Phase: {workflow?.phase}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Overall Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="pt-2">
              <ProgressBar value={project.progress} />
              <div className="text-xs mt-2 text-gray-500">{project.progress}% complete</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* --- Edit/View Document (prominent) --- */}
      <div className="flex justify-center">
        <Button
          asChild
          className="text-lg px-8 py-4 rounded-lg shadow-lg bg-indigo-600 hover:bg-indigo-700"
        >
          <Link href={editDocUrl} className="flex items-center gap-2">
            <FileEdit className="w-6 h-6" />
            {editor === "tiptap" || editor === "toast" || editor === "codex"
              ? "Edit Document"
              : "View Document"}
          </Link>
        </Button>
      </div>

      {/* --- Approvals Table --- */}
      <Card>
        <CardHeader className="flex flex-row justify-between items-center">
          <CardTitle className="text-lg font-semibold">Approvals</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => setShowAddReviewer((v) => !v)}>
            <PlusCircle className="w-4 h-4 mr-2" /> Add Reviewer
          </Button>
        </CardHeader>
        <CardContent>
          {showAddReviewer && (
            <form
              className="flex items-center gap-2 mb-4"
              onSubmit={e => {
                e.preventDefault();
                handleAddReviewer();
              }}
            >
              <Input
                placeholder="Reviewer Name"
                value={newReviewer.reviewer}
                onChange={e => setNewReviewer(r => ({ ...r, reviewer: e.target.value }))}
                className="max-w-xs"
                required
              />
              <Input
                type="email"
                placeholder="Email Address"
                value={newReviewer.email}
                onChange={e => setNewReviewer(r => ({ ...r, email: e.target.value }))}
                className="max-w-xs"
                required
              />
              <Button type="submit" size="sm">Add</Button>
            </form>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <input
                    type="checkbox"
                    checked={selectedApprovals.length === approvals.length && approvals.length > 0}
                    onChange={e =>
                      setSelectedApprovals(
                        e.target.checked ? approvals.map(a => a.id) : []
                      )
                    }
                  />
                </TableHead>
                <TableHead>Reviewer</TableHead>
                <TableHead>Send to Reviewer</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Status Date</TableHead>
                <TableHead>Actions</TableHead>
                <TableHead>Comments</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {approvals.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedApprovals.includes(a.id)}
                      onChange={e => handleSelectApproval(a.id, e.target.checked)}
                    />
                  </TableCell>
                  <TableCell>{a.reviewer}</TableCell>
                  <TableCell>
                    <Button
                      size="icon"
                      variant="ghost"
                      title="Send email"
                      onClick={() => handleSendEmail(a)}
                    >
                      <Mail className="w-5 h-5" />
                    </Button>
                  </TableCell>
                  <TableCell>
                    <span className={cn(
                      "px-2 py-1 rounded text-xs font-medium",
                      a.state === "approved"
                        ? "bg-green-100 text-green-800"
                        : a.state === "pending"
                        ? "bg-blue-100 text-blue-800"
                        : a.state === "overdue"
                        ? "bg-red-100 text-red-800"
                        : "bg-gray-100 text-gray-700"
                    )}>
                      {a.state}
                    </span>
                  </TableCell>
                  <TableCell>{a.statusDate}</TableCell>
                  <TableCell className="space-x-1">
                    {a.state !== "approved" && (
                      <>
                        <Button size="sm" variant="secondary">Approve (API)</Button>
                        {a.documensoSigId && (
                          <Button asChild size="sm" variant="outline">
                            <Link
                              href={`/documentso/${a.documensoSigId}?returnTo=/projects/${id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Sign in Documenso
                            </Link>
                          </Button>
                        )}
                      </>
                    )}
                    <Button
                      size="icon"
                      variant="ghost"
                      title="Remove Reviewer"
                      onClick={() => handleRemoveReviewer(a.id)}
                    >
                      <Trash className="w-5 h-5" />
                    </Button>
                  </TableCell>
                  <TableCell className="max-w-xs">{a.comments || <span className="text-gray-400">–</span>}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* --- Document Comments & Disposition Table --- */}
      <Card>
        <CardHeader className="flex flex-row justify-between items-center">
          <CardTitle className="text-lg font-semibold">Document Comments and Disposition</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => setShowAddComment((v) => !v)}>
            <PlusCircle className="w-4 h-4 mr-2" /> Add Comment
          </Button>
        </CardHeader>
        <CardContent>
          {showAddComment && (
            <form
              className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-4"
              onSubmit={e => {
                e.preventDefault();
                handleAddComment();
              }}
            >
              <Input
                placeholder="Reviewer Name"
                value={newComment.reviewer}
                onChange={e => setNewComment(r => ({ ...r, reviewer: e.target.value }))}
                className="col-span-1"
                required
              />
              <Input
                placeholder="Routing"
                value={newComment.routing}
                onChange={e => setNewComment(r => ({ ...r, routing: e.target.value }))}
                className="col-span-1"
                required
              />
              <Input
                type="email"
                placeholder="Email"
                value={newComment.email}
                onChange={e => setNewComment(r => ({ ...r, email: e.target.value }))}
                className="col-span-1"
                required
              />
              <Input
                placeholder="Page/Para #"
                value={newComment.pagePara}
                onChange={e => setNewComment(r => ({ ...r, pagePara: e.target.value }))}
                className="col-span-1"
                required
              />
              <Input
                placeholder="Comment/Rationale"
                value={newComment.comment}
                onChange={e => setNewComment(r => ({ ...r, comment: e.target.value }))}
                className="col-span-1 md:col-span-2"
                required
              />
              <Input
                placeholder="Recommended Change"
                value={newComment.change}
                onChange={e => setNewComment(r => ({ ...r, change: e.target.value }))}
                className="col-span-1 md:col-span-2"
                required
              />
              <Input
                placeholder="Disposition"
                value={newComment.disposition}
                onChange={e => setNewComment(r => ({ ...r, disposition: e.target.value }))}
                className="col-span-1"
                required
              />
              <Button type="submit" className="col-span-1 md:col-span-4 mt-1">Add</Button>
            </form>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reviewer Name</TableHead>
                <TableHead>Routing</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Page/Para #</TableHead>
                <TableHead>Comment/Rationale</TableHead>
                <TableHead>Recommended Change</TableHead>
                <TableHead>Disposition</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {dispoComments.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>{c.reviewer}</TableCell>
                  <TableCell>{c.routing}</TableCell>
                  <TableCell>{c.email}</TableCell>
                  <TableCell>{c.pagePara}</TableCell>
                  <TableCell className="max-w-xs">{c.comment}</TableCell>
                  <TableCell className="max-w-xs">{c.change}</TableCell>
                  <TableCell>{c.disposition}</TableCell>
                  <TableCell>
                    <Button
                      size="icon"
                      variant="ghost"
                      title="Remove Comment"
                      onClick={() => handleRemoveComment(c.id)}
                    >
                      <Trash className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {dispoComments.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-gray-400 py-6">
                    No comments added.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* --- Audit History --- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Audit History</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 text-sm">
            {logs.map((l, idx) => (
              <li key={idx}>
                {l.timestamp.slice(0, 10)} – {l.action}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
