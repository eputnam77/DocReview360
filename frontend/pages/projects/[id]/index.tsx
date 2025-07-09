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
import { Users2, CheckCircle2, Clock, BarChart2 } from "lucide-react";
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
  state: string;
  documensoSigId?: string;
}

// --- Demo Data (replace with real) ---
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
  phase: "Drafting",
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
];

// --- Components ---
function StatCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: number; color?: string }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <Icon className={`w-8 h-8 ${color || "text-indigo-600"}`} />
        <div>
          <p className="text-xl font-bold leading-none">{value}</p>
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
    // Simulate async fetch
    setTimeout(() => {
      setProject(DEMO_PROJECT); // Replace with real fetch(`/api/projects/${id}`)
      setWorkflow(DEMO_WORKFLOW);
      setApprovals(DEMO_APPROVALS);
      setLogs([
        { timestamp: "2025-07-04", action: "Draft created" },
        { timestamp: "2025-07-04", action: "Initial review started" },
        { timestamp: "2025-07-05", action: "Draft updated" },
      ]);
      setLoading(false);
    }, 300);
  }, [id]);

  if (loading) return <p className="p-4">Loading…</p>;
  if (!project) return <p className="p-4">Project not found.</p>;

  const editor = project.editor ?? "tiptap";
  const editDocUrl = `/editors/${editor}?projectId=${id}&returnTo=/projects/${id}`;

  // --- Status KPI row
  const statAssigned = 1;
  const statCompleted = project.status === "Complete" ? 1 : 0;
  const statInProgress = project.status === "In Progress" ? 1 : 0;
  const statOverdue = project.status === "Overdue" ? 1 : 0;

  return (
    <div className="p-8 space-y-8">
      {/* Header: Document Info Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Project Details</CardTitle>
        </CardHeader>
        <CardContent>
          <Table className="mb-0">
            <TableBody>
              <TableRow>
                <TableHead>Document Id</TableHead>
                <TableCell>{project.id}</TableCell>
              </TableRow>
              <TableRow>
                <TableHead>Document #</TableHead>
                <TableCell>{project.number}</TableCell>
              </TableRow>
              <TableRow>
                <TableHead>Document Type</TableHead>
                <TableCell>{project.type}</TableCell>
              </TableRow>
              <TableRow>
                <TableHead>Document Title</TableHead>
                <TableCell>{project.title}</TableCell>
              </TableRow>
              <TableRow>
                <TableHead>Status</TableHead>
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
              </TableRow>
              <TableRow>
                <TableHead>Progress</TableHead>
                <TableCell className="min-w-[100px] w-32">
                  <ProgressBar value={project.progress} />
                </TableCell>
              </TableRow>
              <TableRow>
                <TableHead>Last Updated</TableHead>
                <TableCell>{project.updated?.slice(0, 10) ?? ""}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Status KPI Stat Row */}
      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-4 max-w-2xl">
        <StatCard icon={Users2} label="Assigned" value={statAssigned} color="text-indigo-600" />
        <StatCard icon={Clock} label="In Progress" value={statInProgress} color="text-orange-600" />
        <StatCard icon={CheckCircle2} label="Completed" value={statCompleted} color="text-emerald-600" />
        <StatCard icon={BarChart2} label="Overdue" value={statOverdue} color="text-red-600" />
      </div>

      {/* Workflow Progress */}
      {workflow && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Workflow Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <WorkflowSteps steps={workflow.steps} />
            <p className="text-xs text-gray-500 mt-1">Current Phase: {workflow.phase}</p>
          </CardContent>
        </Card>
      )}

      {/* Approvals Table */}
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
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Audit History */}
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

      {/* Edit Document Button */}
      <Button asChild>
        <Link href={editDocUrl}>Edit Document</Link>
      </Button>
    </div>
  );
}
