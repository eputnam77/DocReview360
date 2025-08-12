import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tabs, TabsList, TabsTrigger, TabsContent,
} from "@/components/ui/tabs";
import {
  LayoutDashboard, Users2, FileText, ShieldCheck, BarChart2, AlertTriangle, ActivitySquare, Server, Lock, Settings, KeySquare,
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, LineChart, Line,
} from "recharts";

// Chart color palette
const COLORS = [
  "#6366f1", "#22d3ee", "#f59e42", "#4ade80", "#a78bfa", "#f87171", "#f472b6", "#818cf8",
];

// --- Data Types ---
type Stats = {
  users: number; documents: number; activeSessions: number; apiErrors: number; failedLogins: number; roles: number;
};
type Activity = { date: string; actions: number };
type Log = { timestamp: string; action: string; metadata?: { user?: string; ip?: string } };
type ErrorStat = { type: string; count: number };
type APIMetric = { endpoint: string; requests: number; errors: number };
type RoleStat = { role: string; count: number };
type SessionStat = { id: string; user: string; ip: string; active: boolean; started: string };
type HealthStat = { name: string; value: string; status: "ok" | "warning" | "down" };

export default function AdminDashboardPage() {
  // --- State ---
  const [stats, setStats] = useState<Stats>({
    users: 0, documents: 0, activeSessions: 0, apiErrors: 0, failedLogins: 0, roles: 0,
  });
  const [logs, setLogs] = useState<Log[]>([]);
  const [activityData, setActivityData] = useState<Activity[]>([]);
  const [errorStats, setErrorStats] = useState<ErrorStat[]>([]);
  const [apiMetrics, setApiMetrics] = useState<APIMetric[]>([]);
  const [roleStats, setRoleStats] = useState<RoleStat[]>([]);
  const [sessionStats, setSessionStats] = useState<SessionStat[]>([]);
  const [healthStats, setHealthStats] = useState<HealthStat[]>([]);
  const [showPicker, setShowPicker] = useState(false);

  // Widget visibility state
  const DASHBOARD_KEYS = [
    "kpi", "roles", "sessions", "api", "health", "activity", "errors", "logs",
  ];
  const DEFAULT_VISIBLE = ["kpi", "roles", "sessions", "api", "health", "activity", "errors", "logs"];
  // Initialize with a stable value for SSR; hydrate from localStorage after mount
  const [visibleDashboards, setVisibleDashboards] = useState<string[]>(DEFAULT_VISIBLE);
  useEffect(() => {
    try {
      if (typeof window !== "undefined") {
        const stored = localStorage.getItem("visibleAdminDashboards");
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed)) setVisibleDashboards(parsed);
        }
      }
    } catch {
      // ignore JSON/localStorage errors
    }
  }, []);
  const toggleDashboard = (key: string) => {
    setVisibleDashboards((prev) => {
      const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
      localStorage.setItem("visibleAdminDashboards", JSON.stringify(next));
      return next;
    });
  };

  const API = process.env.NEXT_PUBLIC_API_BASE ?? "";
  const fallback = {
    stats: { users: 38, documents: 182, activeSessions: 6, apiErrors: 2, failedLogins: 3, roles: 4 },
    logs: [
      { timestamp: "2025-07-04T16:10", action: "User created", metadata: { user: "Jane Doe", ip: "10.0.1.5" } },
      { timestamp: "2025-07-04T15:15", action: "Failed login", metadata: { user: "unknown", ip: "10.0.2.13" } },
      { timestamp: "2025-07-04T14:05", action: "API 500 error", metadata: { user: "Service", ip: "127.0.0.1" } },
      { timestamp: "2025-07-04T13:20", action: "Permission change", metadata: { user: "Admin", ip: "10.0.1.1" } },
    ] as Log[],
    activity: [
      { date: "2025-07-01", actions: 8 },
      { date: "2025-07-02", actions: 12 },
      { date: "2025-07-03", actions: 10 },
      { date: "2025-07-04", actions: 13 },
      { date: "2025-07-05", actions: 9 },
    ] as Activity[],
    errors: [
      { type: "API Error", count: 2 },
      { type: "Login Failure", count: 3 },
      { type: "Permission Denied", count: 1 },
    ] as ErrorStat[],
    metrics: [
      { endpoint: "/api/documents", requests: 320, errors: 1 },
      { endpoint: "/api/users", requests: 98, errors: 0 },
      { endpoint: "/api/auth", requests: 52, errors: 2 },
    ] as APIMetric[],
    roles: [
      { role: "Admin", count: 2 },
      { role: "Manager", count: 5 },
      { role: "Tech Writer", count: 18 },
      { role: "SME", count: 13 },
    ] as RoleStat[],
    sessions: [
      { id: "S1", user: "Jane Doe", ip: "10.0.1.5", active: true, started: "2025-07-04T15:01" },
      { id: "S2", user: "John Smith", ip: "10.0.2.13", active: true, started: "2025-07-04T15:10" },
      { id: "S3", user: "Alice Lee", ip: "10.0.2.55", active: true, started: "2025-07-04T15:30" },
    ] as SessionStat[],
    health: [
      { name: "Database", value: "OK", status: "ok" },
      { name: "API Server", value: "OK", status: "ok" },
      { name: "Worker", value: "Delayed", status: "warning" },
      { name: "Email Service", value: "Down", status: "down" },
    ] as HealthStat[],
  };

  const { data, isError } = useQuery<any>({
    queryKey: ["admin-dashboard"],
    queryFn: async () => {
      const r = await fetch(`${API}/dashboard/admin`);
      return r.ok ? r.json() : null;
    },
  });

  useEffect(() => {
    if (data) {
      setStats({
        users: data.summary?.projects ?? fallback.stats.users,
        documents: data.summary?.documents ?? fallback.stats.documents,
        activeSessions: data.status?.workflows ?? fallback.stats.activeSessions,
        apiErrors: fallback.stats.apiErrors,
        failedLogins: fallback.stats.failedLogins,
        roles: fallback.stats.roles,
      });
    } else if (isError) {
      setStats(fallback.stats);
    }

    if (!data && isError) {
      setLogs(fallback.logs);
      setActivityData(fallback.activity);
      setErrorStats(fallback.errors);
      setApiMetrics(fallback.metrics);
      setRoleStats(fallback.roles);
      setSessionStats(fallback.sessions);
      setHealthStats(fallback.health);
    }
  }, [data, isError]);

  // KPI Card
  const StatCard = ({
    icon: Icon, label, value, color,
  }: { icon: React.ElementType; label: string; value: number; color?: string }) => (
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

  // Dashboard Registry
  const DASHBOARDS = [
    {
      key: "kpi", label: "Key System Stats", icon: LayoutDashboard,
      component: (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard icon={Users2} label="Users" value={stats.users} color="text-indigo-600" />
          <StatCard icon={FileText} label="Documents" value={stats.documents} color="text-cyan-600" />
          <StatCard icon={BarChart2} label="Active Sessions" value={stats.activeSessions} color="text-emerald-600" />
          <StatCard icon={AlertTriangle} label="API Errors" value={stats.apiErrors} color="text-red-600" />
          <StatCard icon={AlertTriangle} label="Failed Logins" value={stats.failedLogins} color="text-orange-600" />
          <StatCard icon={Lock} label="Roles/Permissions" value={stats.roles} color="text-purple-600" />
        </div>
      ),
    },
    {
      key: "roles", label: "User Roles Breakdown", icon: Lock,
      component: (
        <Card>
          <CardHeader><CardTitle>User Roles Breakdown</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={roleStats}
                  dataKey="count"
                  nameKey="role"
                  cx="50%" cy="50%" outerRadius={80}
                  label={({ role, count }) => `${role}: ${count}`}
                >
                  {roleStats.map((entry, idx) => (
                    <Cell key={`cell-role-${idx}`} fill={COLORS[idx % COLORS.length]} />
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
      key: "sessions", label: "Active Sessions", icon: ActivitySquare,
      component: (
        <Card>
          <CardHeader><CardTitle>Active Sessions</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {sessionStats.map((s) => (
                <li key={s.id} className="flex gap-4 items-center border-b last:border-none pb-2">
                  <Users2 className="w-4 h-4 text-indigo-500" />
                  <span>{s.user}</span>
                  <span className="text-xs text-gray-500">{s.ip}</span>
                  <span className="ml-auto text-xs">{s.active ? "Active" : "Inactive"}</span>
                  <span className="ml-2 text-xs text-gray-400">{s.started.slice(0, 10)}</span>
                </li>
              ))}
              {sessionStats.length === 0 && <li>No active sessions.</li>}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "api", label: "API Usage & Errors", icon: Server,
      component: (
        <Card>
          <CardHeader><CardTitle>API Usage & Errors</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={apiMetrics}>
                <XAxis dataKey="endpoint" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="requests" fill="#6366f1" />
                <Bar dataKey="errors" fill="#f87171" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "health", label: "System Health", icon: Settings,
      component: (
        <Card>
          <CardHeader><CardTitle>System Health</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {healthStats.map((h, i) => (
                <li key={i} className="flex gap-2 items-center">
                  <ShieldCheck className={
                    h.status === "ok" ? "w-4 h-4 text-emerald-500"
                    : h.status === "warning" ? "w-4 h-4 text-yellow-500"
                    : "w-4 h-4 text-red-500"
                  } />
                  <span className="font-semibold">{h.name}</span>
                  <span className={
                    h.status === "ok" ? "text-emerald-700"
                    : h.status === "warning" ? "text-yellow-700"
                    : "text-red-700"
                  }>
                    {h.value}
                  </span>
                </li>
              ))}
              {healthStats.length === 0 && <li>No health data.</li>}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "activity", label: "System Activity", icon: BarChart2,
      component: (
        <Card>
          <CardHeader><CardTitle>System Activity (Last 5 Days)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={activityData}>
                <XAxis dataKey="date" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="actions" stroke="#6366f1" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "errors", label: "System Errors", icon: AlertTriangle,
      component: (
        <Card>
          <CardHeader><CardTitle>System Errors</CardTitle></CardHeader>
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
      key: "logs", label: "Audit & Log Feed", icon: ShieldCheck,
      component: (
        <Tabs defaultValue="logs" className="mt-2 space-y-2">
          <TabsList>
            <TabsTrigger value="logs">Recent System Events</TabsTrigger>
            <TabsTrigger value="users">Active Users</TabsTrigger>
          </TabsList>
          <TabsContent value="logs">
            <Card>
              <CardHeader><CardTitle>Audit Log Feed</CardTitle></CardHeader>
              <CardContent className="max-h-64 overflow-y-auto">
                <ul className="text-sm space-y-1">
                  {logs.map((l, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="inline-block w-24 text-gray-400">{l.timestamp.slice(0, 10)}</span>
                      <span className="font-medium">{l.action}</span>
                      {l.metadata?.user && <span className="ml-2 text-indigo-600">@{l.metadata.user}</span>}
                      {l.metadata?.ip && <span className="ml-2 text-teal-600">{l.metadata.ip}</span>}
                    </li>
                  ))}
                  {logs.length === 0 && <li className="text-muted-foreground">No recent activity.</li>}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="users">
            <Card>
              <CardHeader><CardTitle>Recent Active Users</CardTitle></CardHeader>
              <CardContent>
                <ul className="text-sm space-y-2">
                  {sessionStats.map((s, idx) => (
                    <li key={s.id} className="flex items-center gap-2">
                      <span className="font-semibold">{idx + 1}.</span>
                      <span className="flex-1">{s.user}</span>
                      <span className="text-indigo-700">{s.ip}</span>
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
          Admin Dashboard
        </h1>
        <Button variant="outline" size="sm" onClick={() => setShowPicker((v) => !v)}>
          Customize Dashboard
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
