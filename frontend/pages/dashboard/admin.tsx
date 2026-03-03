import React, { useEffect, useMemo, useState } from "react";
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
import { authenticatedFetch } from "@/lib/api";

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
interface RolePermissionSummary { role: string; permissions: string[]; count: number; default_permissions: string[]; default_count: number; is_default: boolean; }
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
  const [rolePermissions, setRolePermissions] = useState<RolePermissionSummary[]>([]);
  const [sessionStats, setSessionStats] = useState<SessionStat[]>([]);
  const [healthStats, setHealthStats] = useState<HealthStat[]>([]);
  const [userCount, setUserCount] = useState(0);
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

  const { data, isError } = useQuery<any>({
    queryKey: ["admin-dashboard"],
    queryFn: async () => {
      const r = await authenticatedFetch("/dashboard/admin");
      return r.ok ? r.json() : null;
    },
  });

  const loadRolePermissions = () => {
    authenticatedFetch("/rbac/role-permissions")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: RolePermissionSummary[]) => {
        setRolePermissions(Array.isArray(data) ? data : []);
      })
      .catch(() => setRolePermissions([]));
  };

  useEffect(() => {
    loadRolePermissions();
    authenticatedFetch("/users")
      .then((r) => (r.ok ? r.json() : []))
      .then((users: any[]) => {
        const list = Array.isArray(users) ? users : [];
        setUserCount(list.length);
        const roleCounts = new Map<string, number>();
        list.forEach((user) => {
          const roles = Array.isArray(user.roles) ? user.roles : [];
          roles.forEach((role: string) => {
            if (!role) return;
            roleCounts.set(role, (roleCounts.get(role) ?? 0) + 1);
          });
        });
        setRoleStats(
          Array.from(roleCounts.entries()).map(([role, count]) => ({
            role,
            count,
          })),
        );
      })
      .catch(() => {
        setUserCount(0);
        setRoleStats([]);
      });
  }, []);

  const rolePermissionMap = useMemo(() => {
    const mapping = new Map<string, RolePermissionSummary>();
    rolePermissions.forEach((item) => mapping.set(item.role, item));
    return mapping;
  }, [rolePermissions]);

  useEffect(() => {
    if (data) {
      setStats({
        users: userCount,
        documents: data.summary?.documents ?? 0,
        activeSessions: data.status?.workflows ?? 0,
        apiErrors: 0,
        failedLogins: 0,
        roles: roleStats.length,
      });
      setLogs([]);
      setActivityData([]);
      setErrorStats([]);
      setApiMetrics([]);
      setSessionStats([]);
      setHealthStats([]);
    } else if (isError) {
      setStats({
        users: 0,
        documents: 0,
        activeSessions: 0,
        apiErrors: 0,
        failedLogins: 0,
        roles: 0,
      });
      setLogs([]);
      setActivityData([]);
      setErrorStats([]);
      setApiMetrics([]);
      setSessionStats([]);
      setHealthStats([]);
    }
  }, [data, isError, roleStats.length, userCount]);

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
                  label={({ role, count }) => {
                    const permCount = rolePermissionMap.get(role)?.count ?? 0;
                    return `${role} (${permCount} perms): ${count}`;
                  }}
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
