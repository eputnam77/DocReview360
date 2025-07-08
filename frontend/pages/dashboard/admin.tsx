import React, { useEffect, useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  Users2,
  Clock,
  BarChart2,
  ShieldCheck,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

// Sample color palette for charts
const COLORS = [
  "#6366f1", // Indigo
  "#22d3ee", // Cyan
  "#f59e42", // Orange
  "#4ade80", // Green
  "#a78bfa", // Purple
  "#f87171", // Red
];

type Stats = {
  projects: number;
  users: number;
  documents: number;
  approvals: number;
  inProgress: number;
  completed: number;
  overdue: number;
  active: number;
};

type StatusData = { name: string; value: number };
type UserLeaderboard = { user: string; projects: number };
type Activity = { date: string; actions: number };
type Log = { timestamp: string; action: string; metadata?: { user?: string; project?: string } };

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<Stats>({
    projects: 0,
    users: 0,
    documents: 0,
    approvals: 0,
    inProgress: 0,
    completed: 0,
    overdue: 0,
    active: 0,
  });
  const [statusData, setStatusData] = useState<StatusData[]>([]);
  const [userLeaderboard, setUserLeaderboard] = useState<UserLeaderboard[]>([]);
  const [activityData, setActivityData] = useState<Activity[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);

  // Simulated API data – replace with your endpoints
  useEffect(() => {
    fetch("/api/admin/metrics")
      .then((r) => r.json())
      .then(setStats)
      .catch(() =>
        setStats({
          projects: 22,
          users: 14,
          documents: 75,
          approvals: 18,
          inProgress: 6,
          completed: 13,
          overdue: 3,
          active: 10,
        })
      );

    // Status chart data
    setStatusData([
      { name: "In Progress", value: 6 },
      { name: "Completed", value: 13 },
      { name: "Overdue", value: 3 },
    ]);

    // User leaderboard
    setUserLeaderboard([
      { user: "Jane Doe", projects: 7 },
      { user: "John Smith", projects: 5 },
      { user: "Alice Lee", projects: 4 },
      { user: "Team Beta", projects: 3 },
    ]);

    // Activity chart
    setActivityData([
      { date: "2025-07-01", actions: 4 },
      { date: "2025-07-02", actions: 6 },
      { date: "2025-07-03", actions: 8 },
      { date: "2025-07-04", actions: 10 },
      { date: "2025-07-05", actions: 7 },
    ]);

    // Recent log/audit feed
    setLogs([
      { timestamp: "2025-07-04T16:10", action: "Approved project", metadata: { user: "Jane Doe", project: "AC-002" } },
      { timestamp: "2025-07-03T14:20", action: "Created project", metadata: { user: "Alice Lee", project: "AC-005" } },
      { timestamp: "2025-07-02T10:00", action: "Uploaded document", metadata: { user: "John Smith", project: "AC-001" } },
      { timestamp: "2025-07-01T09:00", action: "Assigned reviewer", metadata: { user: "Team Beta", project: "AC-004" } },
    ]);
  }, []);

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
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{label}</p>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <h1 className="text-3xl font-bold flex gap-2 items-center">
        <ShieldCheck className="w-7 h-7 text-purple-700" /> Admin Dashboard
      </h1>

      {/* KPI Row */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={FolderOpen} label="Projects" value={stats.projects} color="text-indigo-600" />
        <StatCard icon={Users2} label="Users" value={stats.users} color="text-emerald-600" />
        <StatCard icon={FileText} label="Documents" value={stats.documents} color="text-cyan-600" />
        <StatCard icon={Clock} label="Active Workflows" value={stats.active} color="text-yellow-600" />
      </div>

      {/* Admin Visuals */}
      <div className="grid gap-8 md:grid-cols-2">
        {/* Pie Chart: Project Status */}
        <Card>
          <CardHeader>
            <CardTitle>Project Status Breakdown</CardTitle>
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
                    <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Bar Chart: User Leaderboard */}
        <Card>
          <CardHeader>
            <CardTitle>User/Team Leaderboard</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={userLeaderboard}>
                <XAxis dataKey="user" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="projects" fill="#6366f1" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Activity Line Chart */}
      <Card>
        <CardHeader>
          <CardTitle>System Activity (Last 5 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={activityData}>
              <XAxis dataKey="date" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="actions" fill="#f59e42" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Audit/Log Feed */}
      <Tabs defaultValue="logs" className="mt-6 space-y-4">
        <TabsList>
          <TabsTrigger value="logs">Recent Activity</TabsTrigger>
          <TabsTrigger value="users">Top Users</TabsTrigger>
        </TabsList>
        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle>Audit Feed</CardTitle>
            </CardHeader>
            <CardContent className="max-h-64 overflow-y-auto">
              <ul className="text-sm space-y-1">
                {logs.map((l, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="inline-block w-24 text-gray-400">
                      {l.timestamp.slice(0, 10)}
                    </span>
                    <span className="font-medium">{l.action}</span>
                    {l.metadata?.user && (
                      <span className="ml-2 text-indigo-600">@{l.metadata.user}</span>
                    )}
                    {l.metadata?.project && (
                      <span className="ml-2 text-teal-600">{l.metadata.project}</span>
                    )}
                  </li>
                ))}
                {logs.length === 0 && (
                  <li className="text-muted-foreground">No recent activity.</li>
                )}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <CardTitle>Top Users/Teams</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-2">
                {userLeaderboard.map((u, idx) => (
                  <li key={u.user} className="flex items-center gap-2">
                    <span className="font-semibold">{idx + 1}.</span>
                    <span className="flex-1">{u.user}</span>
                    <span className="text-indigo-700">{u.projects} projects</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

