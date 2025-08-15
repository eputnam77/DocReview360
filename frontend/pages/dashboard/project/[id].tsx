import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  BarChart2,
  FolderOpen,
  Users2,
  Clock,
  CheckCircle2,
  FileText,
  ChevronRight,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

// Color palette for charts
const COLORS = [
  "#6366f1", // Indigo
  "#22d3ee", // Cyan
  "#4ade80", // Green
  "#f59e42", // Orange
  "#a78bfa", // Purple
  "#f87171", // Red
];

type Project = {
  id: string;
  title: string;
  status: "Draft" | "In Progress" | "Under Review" | "Approved" | "Rejected";
  assignedTo: string;
  dueDate: string;
  steps: { name: string; status: string; completed?: string }[];
  completedSteps: number;
  totalSteps: number;
  documents: number;
  currentPhaseId?: string | null;
};

type Log = { timestamp: string; action: string };

export default function ProjectDashboardPage() {
  const router = useRouter();
  const { id } = router.query;
  const [project, setProject] = useState<Project | null>(null);
  const [logs, setLogs] = useState<Log[]>([]);

  // Simulate API calls; swap for your endpoints!
  useEffect(() => {
    if (!id) return;
    // Fetch project
    setProject({
      id: id as string,
      title: "AC-101 – Policy Update for Part 23",
      status: "In Progress",
      assignedTo: "Jane Doe",
      dueDate: "2025-07-15",
      steps: [
        { name: "Draft", status: "Completed", completed: "2025-07-01" },
        { name: "SME Review", status: "Completed", completed: "2025-07-03" },
        { name: "Legal Review", status: "In Progress" },
        { name: "Final Approval", status: "Pending" },
      ],
      completedSteps: 2,
      totalSteps: 4,
      documents: 3,
    });
    // Fetch logs
    setLogs([
      { timestamp: "2025-07-03T15:10", action: "SME Review completed" },
      { timestamp: "2025-07-02T12:05", action: "Draft submitted" },
      { timestamp: "2025-07-01T09:00", action: "Project created" },
    ]);
  }, [id]);

  if (!project) return <div className="p-8">Loading…</div>;

  // Chart data: steps breakdown
  const stepsPieData = [
    { name: "Completed", value: project.completedSteps },
    { name: "Remaining", value: project.totalSteps - project.completedSteps },
  ];

  // Timeline icon helper
  const statusIcon = (status: string) => {
    if (status === "Completed")
      return <CheckCircle2 className="text-emerald-600 w-5 h-5" />;
    if (status === "In Progress")
      return <Clock className="text-orange-500 w-5 h-5 animate-pulse" />;
    return <ChevronRight className="text-gray-400 w-5 h-5" />;
  };

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <h1 className="text-2xl font-bold flex gap-2 items-center">
        <FolderOpen className="w-7 h-7 text-indigo-600" /> {project.title}
      </h1>

      {/* KPI Cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <Users2 className="w-8 h-8 text-indigo-600" />
            <div>
              <p className="text-2xl font-bold">{project.assignedTo}</p>
              <p className="text-xs text-gray-500 mt-1">Assigned To</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <FileText className="w-8 h-8 text-cyan-600" />
            <div>
              <p className="text-2xl font-bold">{project.documents}</p>
              <p className="text-xs text-gray-500 mt-1">Documents</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <Clock className="w-8 h-8 text-yellow-500" />
            <div>
              <p className="text-2xl font-bold">{project.dueDate}</p>
              <p className="text-xs text-gray-500 mt-1">Due Date</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <BarChart2 className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-2xl font-bold">
                {project.completedSteps}/{project.totalSteps}
              </p>
              <p className="text-xs text-gray-500 mt-1">Steps Complete</p>
              <Progress
                value={(100 * project.completedSteps) / project.totalSteps}
                className="h-2 mt-1"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Step Breakdown Pie Chart */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Step Completion</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={stepsPieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {stepsPieData.map((entry, idx) => (
                    <Cell
                      key={`cell-${idx}`}
                      fill={COLORS[idx % COLORS.length]}
                    />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        {/* Timeline */}
        <Card>
          <CardHeader>
            <CardTitle>Workflow Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {project.steps.map((step, idx) => (
                <li key={step.name} className="flex items-center gap-3">
                  {statusIcon(step.status)}
                  <span className="font-medium">{step.name}</span>
                  <span
                    className={`ml-2 px-2 py-0.5 text-xs rounded
                    ${
                      step.status === "Completed"
                        ? "bg-emerald-100 text-emerald-700"
                        : step.status === "In Progress"
                          ? "bg-orange-100 text-orange-700"
                          : "bg-gray-100 text-gray-500"
                    }
                  `}
                  >
                    {step.status}
                  </span>
                  {step.completed && (
                    <span className="ml-3 text-xs text-gray-400">
                      {step.completed}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Project Activity Feed */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent className="max-h-56 overflow-y-auto">
          <ul className="space-y-2 text-sm">
            {logs.map((log, idx) => (
              <li key={idx} className="flex gap-2">
                <span className="inline-block w-24 text-gray-400">
                  {log.timestamp.slice(0, 10)}
                </span>
                <span>{log.action}</span>
              </li>
            ))}
            {logs.length === 0 && (
              <li className="text-muted-foreground">No recent activity.</li>
            )}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
