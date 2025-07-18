import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ChatBot } from "@/components";
import {
  LayoutDashboard,
  FolderOpen,
  Users2,
  CheckCircle2,
  Clock,
  BarChart2,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

// Color palette for charts
const COLORS = [
  "#6366f1", // Indigo
  "#22d3ee", // Cyan
  "#4ade80", // Green
  "#f59e42", // Orange
  "#a78bfa", // Purple
];

type Stats = {
  assigned: number;
  inProgress: number;
  completed: number;
  overdue: number;
};
type StatusData = { name: string; value: number };
type Activity = { date: string; actions: number };
type Log = {
  timestamp: string;
  action: string;
  metadata?: { project?: string };
};

export default function MainDashboardPage() {
  const [stats, setStats] = useState<Stats>({
    assigned: 4,
    inProgress: 3,
    completed: 7,
    overdue: 1,
  });
  const [statusData, setStatusData] = useState<StatusData[]>([]);
  const [activityData, setActivityData] = useState<Activity[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [projectFilter, setProjectFilter] = useState<string | null>(null);

  // Simulated API calls — replace with your own endpoints!
  useEffect(() => {
    // Summary stats
    setStats({
      assigned: 4,
      inProgress: 3,
      completed: 7,
      overdue: 1,
    });
    // Project status breakdown
    setStatusData([
      { name: "Assigned to Me", value: 4 },
      { name: "In Progress", value: 3 },
      { name: "Completed", value: 7 },
      { name: "Overdue", value: 1 },
    ]);
    // Recent activity line chart
    setActivityData([
      { date: "2025-07-01", actions: 2 },
      { date: "2025-07-02", actions: 4 },
      { date: "2025-07-03", actions: 3 },
      { date: "2025-07-04", actions: 6 },
      { date: "2025-07-05", actions: 5 },
    ]);
    // Project/Audit logs
    setLogs([
      {
        timestamp: "2025-07-05T09:05",
        action: "Review approved",
        metadata: { project: "AC-101" },
      },
      {
        timestamp: "2025-07-04T18:22",
        action: "Draft uploaded",
        metadata: { project: "AC-102" },
      },
      {
        timestamp: "2025-07-03T15:10",
        action: "Project started",
        metadata: { project: "AC-103" },
      },
      {
        timestamp: "2025-07-02T11:32",
        action: "Review comment added",
        metadata: { project: "AC-104" },
      },
      {
        timestamp: "2025-07-01T08:00",
        action: "Project created",
        metadata: { project: "AC-105" },
      },
    ]);
  }, []);

  // Unique projects for filter dropdown
  const projectOptions = Array.from(
    new Set(logs.map((l) => l.metadata?.project).filter(Boolean)),
  ) as string[];

  // KPI card helper
  const StatCard = ({
    icon: Icon,
    label,
    value,
    color,
  }: {
    icon: React.ElementType;
    label: string;
    value: number;
    color?: string;
  }) => (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <Icon className={`w-10 h-10 ${color || "text-indigo-600"}`} />
        <div>
          <p className="text-3xl font-bold leading-none">{value}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {label}
          </p>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <h1 className="text-3xl font-bold flex gap-2 items-center">
        <LayoutDashboard className="w-7 h-7 text-indigo-600" /> Dashboard
      </h1>

      {/* KPI Row */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Users2}
          label="Assigned to Me"
          value={stats.assigned}
          color="text-indigo-600"
        />
        <StatCard
          icon={Clock}
          label="In Progress"
          value={stats.inProgress}
          color="text-orange-600"
        />
        <StatCard
          icon={CheckCircle2}
          label="Completed"
          value={stats.completed}
          color="text-emerald-600"
        />
        <StatCard
          icon={BarChart2}
          label="Overdue"
          value={stats.overdue}
          color="text-red-600"
        />
      </div>

      {/* Visuals */}
      <div className="grid gap-8 md:grid-cols-2">
        {/* Pie Chart: Project Status */}
        <Card>
          <CardHeader>
            <CardTitle>Project Status</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={statusData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {statusData.map((entry, idx) => (
                    <Cell
                      key={`cell-${idx}`}
                      fill={COLORS[idx % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        {/* Line Chart: Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={activityData}>
                <XAxis dataKey="date" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="actions"
                  stroke="#6366f1"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Feed and Tabs */}
      <Tabs defaultValue="projects" className="mt-6 space-y-4">
        <TabsList>
          <TabsTrigger value="projects">Project Feed</TabsTrigger>
          <TabsTrigger value="activity">Activity Feed</TabsTrigger>
        </TabsList>
        <TabsContent value="projects">
          <Card>
            <CardContent className="h-64 overflow-y-auto rounded-lg bg-gray-50 dark:bg-gray-900 p-4">
              <select
                className="mb-2 border rounded p-1"
                value={projectFilter ?? ""}
                onChange={(e) => setProjectFilter(e.target.value || null)}
              >
                <option value="">All projects</option>
                {projectOptions.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
              <ul className="text-sm space-y-1">
                {logs
                  .filter(
                    (l) =>
                      !projectFilter || l.metadata?.project === projectFilter,
                  )
                  .map((l, i) => (
                    <li key={i}>
                      <span className="inline-block w-24 text-gray-400">
                        {l.timestamp.slice(0, 10)}
                      </span>
                      <span className="ml-2">{l.action}</span>
                    </li>
                  ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="activity">
          <Card>
            <CardContent className="h-64 flex items-center justify-center rounded-lg bg-gray-50 dark:bg-gray-900">
              <BarChart2 className="w-16 h-16 text-gray-400" />
              <span className="ml-4 text-gray-500 dark:text-gray-400">
                (Replace with a stacked bar or detailed feed as needed.)
              </span>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      {/* Simple project chat bot */}
      <ChatBot />
    </div>
  );
}
