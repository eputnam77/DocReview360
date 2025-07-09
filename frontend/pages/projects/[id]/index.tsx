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
import { Users2, CheckCircle2, Clock, BarChart2, FileEdit } from "lucide-react";
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
  state: "pending" | "approved" | "overdue" | string;
  documensoSigId?: string;
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
  { id: "appr-1", reviewer: "Jane Doe", state: "pending", documensoSigId: "sig-123" },
  { id: "appr-2", reviewer: "John Smith", state: "approved" },
  { id: "appr-3", reviewer: "Jill Admin", state: "overdue" },
];
const DEMO_LOGS: LogEntry[] = [
  { timestamp: "2025-07-04", action: "Draft created" },
  { timestamp: "2025-07-04", action: "Initial review started" },
  { timestamp: "2025-07-05", action: "Draft updated" },
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
  const [loading, setLoading] = useState(true);

  // Demo fetch logic
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setTimeout(() => {
      setProject(DEMO_PROJECT); // Replace with real fetch(`/api/projects/${id}`)
      setWorkflow(DEMO_WORKFLOW);
      setApprovals(DEMO_APPROVALS);
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
      {approvals.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Approvals</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reviewer</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {approvals.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{a.reviewer}</TableCell>
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
                    <TableCell>
                      {a.state !== "approved" && (
                        <>
                          <Button size="sm" variant="secondary">
                            Approve (API)
                          </Button>
                          {a.documensoSigId && (
                            <Button asChild size="sm" className="ml-2" variant="outline">
                              <Link
                                href={`/documenso/${a.documensoSigId}?return=/projects/${id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                Sign in Documenso
                              </Link>
                            </Button>
                          )}
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

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
