import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tabs, TabsList, TabsTrigger, TabsContent,
} from "@/components/ui/tabs";
import {
  LayoutDashboard, FolderOpen, FileText, Users2, Clock, BarChart2, ShieldCheck, CalendarClock, AlertTriangle, PieChart as PieChartIcon, TrendingUp, UserCheck, BookOpen, CheckCircle2,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line,
} from "recharts";

// --- Chart Colors ---
const COLORS = [
  "#6366f1", // Indigo
  "#22d3ee", // Cyan
  "#f59e42", // Orange
  "#4ade80", // Green
  "#a78bfa", // Purple
  "#f87171", // Red
  "#f472b6", // Pink
  "#818cf8", // Blue
];

// --- Types ---
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
type UserLeaderboard = { user: string; projects: number; workload?: number };
type Activity = { date: string; actions: number };
type Log = { timestamp: string; action: string; metadata?: { user?: string; project?: string } };
type Deadline = { project: string; due: string; daysLeft: number; user: string };
type ErrorStat = { type: string; count: number };
type Turnaround = { phase: string; avgDays: number };
type DocType = { type: string; count: number };
type ReviewStat = { reviewer: string; pending: number };

// --- Main Component ---
export default function ManagerDashboardPage() {
  // --- Data State ---
  const [stats, setStats] = useState<Stats>({
    projects: 0, users: 0, documents: 0, approvals: 0,
    inProgress: 0, completed: 0, overdue: 0, active: 0,
  });
  const [statusData, setStatusData] = useState<StatusData[]>([]);
  const [userLeaderboard, setUserLeaderboard] = useState<UserLeaderboard[]>([]);
  const [activityData, setActivityData] = useState<Activity[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [errorStats, setErrorStats] = useState<ErrorStat[]>([]);
  const [turnarounds, setTurnarounds] = useState<Turnaround[]>([]);
  const [docTypes, setDocTypes] = useState<DocType[]>([]);
  const [reviewStats, setReviewStats] = useState<ReviewStat[]>([]);
  const [showPicker, setShowPicker] = useState(false);

  // --- Customizable dashboard visibility state ---
  const DASHBOARD_KEYS = [
    "kpi", "status", "leaderboard", "activity", "deadlines", "reviews", "errors", "turnaround", "docTypes", "logs",
  ];
  const DEFAULT_VISIBLE = ["kpi", "status", "leaderboard", "activity", "deadlines", "reviews", "logs"];
  const [visibleDashboards, setVisibleDashboards] = useState<string[]>(
    () => JSON.parse(localStorage.getItem("visibleDashboards") || JSON.stringify(DEFAULT_VISIBLE))
  );
  const toggleDashboard = (key: string) => {
    setVisibleDashboards((prev) => {
      const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
      localStorage.setItem("visibleDashboards", JSON.stringify(next));
      return next;
    });
  };

  // --- Simulated Data ---
  useEffect(() => {
    // API fetch stubs (replace with real endpoints)
    setStats({ projects: 22, users: 14, documents: 75, approvals: 18, inProgress: 6, completed: 13, overdue: 3, active: 10 });
    setStatusData([
      { name: "In Progress", value: 6 },
      { name: "Completed", value: 13 },
      { name: "Overdue", value: 3 },
    ]);
    setUserLeaderboard([
      { user: "Jane Doe", projects: 7, workload: 5 },
      { user: "John Smith", projects: 5, workload: 7 },
      { user: "Alice Lee", projects: 4, workload: 4 },
      { user: "Team Beta", projects: 3, workload: 2 },
    ]);
    setActivityData([
      { date: "2025-07-01", actions: 4 },
      { date: "2025-07-02", actions: 6 },
      { date: "2025-07-03", actions: 8 },
      { date: "2025-07-04", actions: 10 },
      { date: "2025-07-05", actions: 7 },
    ]);
    setLogs([
      { timestamp: "2025-07-04T16:10", action: "Approved project", metadata: { user: "Jane Doe", project: "AC-002" } },
      { timestamp: "2025-07-03T14:20", action: "Created project", metadata: { user: "Alice Lee", project: "AC-005" } },
      { timestamp: "2025-07-02T10:00", action: "Uploaded document", metadata: { user: "John Smith", project: "AC-001" } },
      { timestamp: "2025-07-01T09:00", action: "Assigned reviewer", metadata: { user: "Team Beta", project: "AC-004" } },
    ]);
    setDeadlines([
      { project: "AC-002", due: "2025-07-07", daysLeft: 3, user: "Jane Doe" },
      { project: "AC-005", due: "2025-07-08", daysLeft: 4, user: "Alice Lee" },
      { project: "AC-001", due: "2025-07-09", daysLeft: 5, user: "John Smith" },
    ]);
    setErrorStats([
      { type: "Formatting Error", count: 5 },
      { type: "Missing Heading", count: 3 },
      { type: "Accessibility", count: 2 },
      { type: "Incorrect Acronym", count: 1 },
    ]);
    setTurnarounds([
      { phase: "Draft", avgDays: 5.2 },
      { phase: "Review", avgDays: 3.1 },
      { phase: "Approval", avgDays: 2.5 },
    ]);
    setDocTypes([
      { type: "AC", count: 30 },
      { type: "Order", count: 18 },
      { type: "Memo", count: 12 },
      { type: "TSO", count: 10 },
      { type: "Other", count: 5 },
    ]);
    setReviewStats([
      { reviewer: "Jane Doe", pending: 2 },
      { reviewer: "John Smith", pending: 1 },
      { reviewer: "Team Beta", pending: 1 },
    ]);
  }, []);

  // --- KPI Card ---
  const StatCard = ({
    icon: Icon, label, value, color,
  }: { icon: React.ElementType, label: string, value: number, color?: string }) => (
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

  // --- Dashboard Widget Registry ---
  const DASHBOARDS = [
    {
      key: "kpi",
      label: "Key Performance Indicators",
      icon: LayoutDashboard,
      component: (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={FolderOpen} label="Projects" value={stats.projects} color="text-indigo-600" />
          <StatCard icon={Users2} label="Users" value={stats.users} color="text-emerald-600" />
          <StatCard icon={FileText} label="Documents" value={stats.documents} color="text-cyan-600" />
          <StatCard icon={Clock} label="Active Workflows" value={stats.active} color="text-yellow-600" />
        </div>
      ),
    },
    {
      key: "status",
      label: "Project Status Breakdown",
      icon: PieChartIcon,
      component: (
        <Card>
          <CardHeader><CardTitle>Project Status Breakdown</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={statusData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%" cy="50%" outerRadius={80}
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
      ),
    },
    {
      key: "leaderboard",
      label: "User/Team Leaderboard",
      icon: BarChart2,
      component: (
        <Card>
          <CardHeader><CardTitle>User/Team Leaderboard</CardTitle></CardHeader>
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
      ),
    },
    {
      key: "activity",
      label: "System Activity",
      icon: TrendingUp,
      component: (
        <Card>
          <CardHeader><CardTitle>System Activity (Last 5 Days)</CardTitle></CardHeader>
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
      ),
    },
    {
      key: "deadlines",
      label: "Upcoming Deadlines",
      icon: CalendarClock,
      component: (
        <Card>
          <CardHeader><CardTitle>Upcoming Deadlines (next 7 days)</CardTitle></CardHeader>
          <CardContent>
            <ul className="text-sm space-y-2">
              {deadlines.map((d, i) => (
                <li key={i} className="flex items-center gap-3">
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  <span className="font-bold">{d.project}</span>
                  <span>due <span className="text-red-500">{d.due}</span></span>
                  <span className="ml-2 text-indigo-700">@{d.user}</span>
                  <span className="ml-auto text-xs text-gray-500">{d.daysLeft} days left</span>
                </li>
              ))}
              {deadlines.length === 0 && <li>No upcoming deadlines.</li>}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "reviews",
      label: "Pending Reviews",
      icon: UserCheck,
      component: (
        <Card>
          <CardHeader><CardTitle>Pending Reviews by User</CardTitle></CardHeader>
          <CardContent>
            <ul className="text-sm space-y-2">
              {reviewStats.map((r, i) => (
                <li key={i} className="flex items-center gap-3">
                  <CheckCircle2 className="w-4 h-4 text-cyan-600" />
                  <span className="font-bold">{r.reviewer}</span>
                  <span className="ml-2 text-amber-700">{r.pending} pending</span>
                </li>
              ))}
              {reviewStats.length === 0 && <li>All reviews up to date.</li>}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "errors",
      label: "Quality/Error Stats",
      icon: AlertTriangle,
      component: (
        <Card>
          <CardHeader><CardTitle>Top Quality/Formatting Issues</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={errorStats}>
                <XAxis dataKey="type" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#f87171" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "turnaround",
      label: "Turnaround Times",
      icon: Clock,
      component: (
        <Card>
          <CardHeader><CardTitle>Average Turnaround Time (days per phase)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={turnarounds}>
                <XAxis dataKey="phase" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="avgDays" stroke="#4ade80" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "docTypes",
      label: "Document Type Breakdown",
      icon: BookOpen,
      component: (
        <Card>
          <CardHeader><CardTitle>Document Type Breakdown</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={docTypes}
                  dataKey="count"
                  nameKey="type"
                  cx="50%" cy="50%" outerRadius={80}
                  label={({ type, count }) => `${type}: ${count}`}
                >
                  {docTypes.map((entry, idx) => (
                    <Cell key={`cell-doc-${idx}`} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "logs",
      label: "Audit/Activity Feed",
      icon: ShieldCheck,
      component: (
        <Tabs defaultValue="logs" className="mt-2 space-y-2">
          <TabsList>
            <TabsTrigger value="logs">Recent Activity</TabsTrigger>
            <TabsTrigger value="users">Top Users</TabsTrigger>
          </TabsList>
          <TabsContent value="logs">
            <Card>
              <CardHeader><CardTitle>Audit Feed</CardTitle></CardHeader>
              <CardContent className="max-h-64 overflow-y-auto">
                <ul className="text-sm space-y-1">
                  {logs.map((l, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="inline-block w-24 text-gray-400">{l.timestamp.slice(0, 10)}</span>
                      <span className="font-medium">{l.action}</span>
                      {l.metadata?.user && <span className="ml-2 text-indigo-600">@{l.metadata.user}</span>}
                      {l.metadata?.project && <span className="ml-2 text-teal-600">{l.metadata.project}</span>}
                    </li>
                  ))}
                  {logs.length === 0 && <li className="text-muted-foreground">No recent activity.</li>}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="users">
            <Card>
              <CardHeader><CardTitle>Top Users/Teams</CardTitle></CardHeader>
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
      ),
    },
  ];

  // --- Render ---
  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex gap-2 items-center">
          <ShieldCheck className="w-7 h-7 text-purple-700" />
          Manager & Senior TW Dashboard
        </h1>
        <Button variant="outline" size="sm" onClick={() => setShowPicker((v) => !v)}>
          Customize Dashboards
        </Button>
      </div>
      {/* Picker Modal */}
      {showPicker && (
        <div className="fixed left-0 top-0 w-full h-full bg-black bg-opacity-40 z-40 flex justify-center items-center">
          <div className="bg-white dark:bg-gray-900 shadow-2xl rounded-lg p-6 w-96">
            <h3 className="font-bold mb-2 flex gap-2 items-center">
              <LayoutDashboard className="w-5 h-5" />
              Select dashboards to show
            </h3>
            <div className="space-y-2">
              {DASHBOARDS.map((db) => (
                <label key={db.key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={visibleDashboards.includes(db.key)}
                    onChange={() => toggleDashboard(db.key)}
                  />
                  <db.icon className="w-4 h-4" />
                  <span>{db.label}</span>
                </label>
              ))}
            </div>
            <div className="flex justify-end mt-4">
              <Button onClick={() => setShowPicker(false)} size="sm">
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* Main Dashboard Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {DASHBOARDS.filter((db) => visibleDashboards.includes(db.key)).map((db) => (
          <div key={db.key}>{db.component}</div>
        ))}
      </div>
    </div>
  );
}
