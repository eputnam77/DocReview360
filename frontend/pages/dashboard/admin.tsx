import React, { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tabs, TabsList, TabsTrigger, TabsContent,
} from "@/components/ui/tabs";
import {
  LayoutDashboard, Users2, FileText, ShieldCheck, BarChart2, AlertTriangle, ActivitySquare, Server, Lock, Settings, KeySquare, Award,
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
type Log = {
  id: string;
  timestamp: string;
  action: string;
  user_id?: string | null;
  ip_address?: string | null;
  severity?: "info" | "warning" | "error";
};
type ErrorStat = { type: string; count: number };
type APIMetric = { endpoint: string; requests: number; errors: number };
type RoleStat = { role: string; count: number };
interface RolePermissionSummary { role: string; permissions: string[]; count: number; default_permissions: string[]; default_count: number; is_default: boolean; }
type SessionStat = { id: string; user: string; summary: string; active: boolean; lastSeen: string };
type HealthStat = { name: string; value: string; status: "ok" | "warning" | "down" };
type QualityMetrics = { avg_score: number; docs_with_scores: number; high_quality_count: number; needs_improvement_count: number };

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
  const [quality, setQuality] = useState<QualityMetrics | null>(null);
  const [showPicker, setShowPicker] = useState(false);

  // Widget visibility state
  const DASHBOARD_KEYS = [
    "kpi", "roles", "sessions", "api", "health", "activity", "errors", "logs",
  ];
  const DEFAULT_VISIBLE = ["kpi", "quality", "roles", "sessions", "api", "health", "activity", "errors", "logs"];
  // Initialize with a stable value for SSR; hydrate from backend after mount
  const [visibleDashboards, setVisibleDashboards] = useState<string[]>(DEFAULT_VISIBLE);
  const [visibilityLoaded, setVisibilityLoaded] = useState(false);

  // Load visibility preferences from backend on mount
  useEffect(() => {
    authenticatedFetch("/dashboard/visibility")
      .then((r) => (r.ok ? r.json() : null))
      .then((prefs: any) => {
        if (prefs && Array.isArray(prefs.widgets) && prefs.widgets.length > 0) {
          setVisibleDashboards(prefs.widgets);
        }
      })
      .catch(() => {
        // ignore — keep defaults
      })
      .finally(() => setVisibilityLoaded(true));
  }, []);

  const toggleDashboard = (key: string) => {
    setVisibleDashboards((prev) => {
      const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
      // Persist to backend
      authenticatedFetch("/dashboard/visibility", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ widgets: next }),
      }).catch(() => {
        // ignore persistence errors
      });
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
    Promise.all([
      authenticatedFetch("/users").then((r) => (r.ok ? r.json() : [])),
      authenticatedFetch("/api/audit?size=25&page=0").then((r) => (r.ok ? r.json() : [])),
    ])
      .then(([usersData, logsData]) => {
        const users = Array.isArray(usersData) ? usersData : [];
        const auditLogs = Array.isArray(logsData) ? logsData : [];

        setUserCount(users.length);

        const roleCounts = new Map<string, number>();
        users.forEach((user) => {
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

        setLogs(auditLogs);

        const byDay = new Map<string, number>();
        const severityCounts = new Map<string, number>();
        const activeUsers = new Map<string, SessionStat>();
        auditLogs.forEach((entry: Log) => {
          const day = entry.timestamp.slice(0, 10);
          byDay.set(day, (byDay.get(day) ?? 0) + 1);
          const severity = entry.severity ?? "info";
          severityCounts.set(severity, (severityCounts.get(severity) ?? 0) + 1);
          if (entry.user_id && !activeUsers.has(entry.user_id)) {
            activeUsers.set(entry.user_id, {
              id: entry.user_id,
              user: entry.user_id,
              summary: entry.ip_address || "Recent activity",
              active: true,
              lastSeen: entry.timestamp,
            });
          }
        });

        setActivityData(
          Array.from(byDay.entries())
            .sort(([left], [right]) => left.localeCompare(right))
            .slice(-5)
            .map(([date, actions]) => ({ date, actions })),
        );
        setErrorStats(
          Array.from(severityCounts.entries()).map(([type, count]) => ({
            type,
            count,
          })),
        );
        setSessionStats(
          activeUsers.size > 0
            ? Array.from(activeUsers.values()).slice(0, 10)
            : users
                .filter((user) => user.active !== false)
                .slice(0, 10)
                .map((user) => ({
                  id: user.username,
                  user: user.username,
                  summary: Array.isArray(user.roles) && user.roles.length > 0
                    ? user.roles.join(", ")
                    : "Active account",
                  active: true,
                  lastSeen: "",
                })),
        );
      })
      .catch(() => {
        setUserCount(0);
        setRoleStats([]);
        setLogs([]);
        setActivityData([]);
        setErrorStats([]);
        setSessionStats([]);
      });
  }, []);

  const rolePermissionMap = useMemo(() => {
    const mapping = new Map<string, RolePermissionSummary>();
    rolePermissions.forEach((item) => mapping.set(item.role, item));
    return mapping;
  }, [rolePermissions]);

  useEffect(() => {
    if (data) {
      const health = Object.entries(data.status ?? {}).map(([name, value]) => {
        const numeric = typeof value === "number" ? value : Number(value);
        const status: HealthStat["status"] =
          Number.isFinite(numeric) && numeric > 0 ? "ok" : "warning";
        return {
          name,
          value: String(value),
          status,
        };
      });
      setStats({
        users: userCount,
        documents: data.summary?.documents ?? 0,
        activeSessions: sessionStats.length,
        apiErrors: errorStats
          .filter((entry) => entry.type === "error")
          .reduce((sum, entry) => sum + entry.count, 0),
        failedLogins: logs.filter((entry) => entry.action === "login_failed").length,
        roles: roleStats.length,
      });
      setApiMetrics([]);
      setHealthStats(health);
      if (data.quality) {
        setQuality(data.quality);
      }
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
      setQuality(null);
    }
  }, [data, errorStats, isError, logs, roleStats.length, sessionStats.length, userCount]);

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

  // Quality score color helper
  const qualityColor = (score: number) => {
    const pct = score * 100;
    if (pct >= 80) return "text-emerald-600";
    if (pct >= 60) return "text-amber-500";
    return "text-red-600";
  };

  // Dashboard Registry
  const DASHBOARDS = [
    {
      key: "kpi", label: "Key System Stats", icon: LayoutDashboard,
      component: (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard icon={Users2} label="Users" value={stats.users} color="text-indigo-600" />
          <StatCard icon={FileText} label="Documents" value={stats.documents} color="text-cyan-600" />
          <StatCard icon={BarChart2} label="Active Users" value={stats.activeSessions} color="text-emerald-600" />
          <StatCard icon={AlertTriangle} label="API Errors" value={stats.apiErrors} color="text-red-600" />
          <StatCard icon={AlertTriangle} label="Failed Logins" value={stats.failedLogins} color="text-orange-600" />
          <StatCard icon={Lock} label="Roles/Permissions" value={stats.roles} color="text-purple-600" />
        </div>
      ),
    },
    {
      key: "quality", label: "Avg Quality Score", icon: Award,
      component: (
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <Award className={`w-10 h-10 ${quality ? qualityColor(quality.avg_score) : "text-gray-400"}`} />
            <div className="flex-1">
              <p className={`text-3xl font-bold leading-none ${quality ? qualityColor(quality.avg_score) : "text-gray-400"}`}>
                {quality && quality.docs_with_scores > 0
                  ? `${Math.round(quality.avg_score * 100)}%`
                  : "—"}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Avg Quality Score</p>
              {quality && quality.docs_with_scores > 0 && (
                <p className="text-xs text-gray-400 mt-1">
                  {quality.docs_with_scores} scored &nbsp;·&nbsp;
                  <span className="text-emerald-600">{quality.high_quality_count} high</span>
                  &nbsp;·&nbsp;
                  <span className="text-red-500">{quality.needs_improvement_count} needs work</span>
                </p>
              )}
              {(!quality || quality.docs_with_scores === 0) && (
                <p className="text-xs text-gray-400 mt-1">No documents scored yet</p>
              )}
            </div>
          </CardContent>
        </Card>
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
                    return `${role} (${permCount} permissions): ${count}`;
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
      key: "sessions", label: "Active Users", icon: ActivitySquare,
      component: (
        <Card>
          <CardHeader><CardTitle>Recently Active Users</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {sessionStats.map((s) => (
                <li key={s.id} className="flex gap-4 items-center border-b last:border-none pb-2">
                  <Users2 className="w-4 h-4 text-indigo-500" />
                  <span>{s.user}</span>
                  <span className="text-xs text-gray-500">{s.summary}</span>
                  <span className="ml-auto text-xs">{s.active ? "Active" : "Inactive"}</span>
                  <span className="ml-2 text-xs text-gray-400">
                    {s.lastSeen ? s.lastSeen.slice(0, 10) : "—"}
                  </span>
                </li>
              ))}
              {sessionStats.length === 0 && <li>No recent user activity.</li>}
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
                      {l.user_id && <span className="ml-2 text-indigo-600">@{l.user_id}</span>}
                      {l.ip_address && <span className="ml-2 text-teal-600">{l.ip_address}</span>}
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
                      <span className="text-indigo-700">{s.summary}</span>
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
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setShowPicker((v) => !v)}
          title="Customize Dashboard"
          aria-label="Customize Dashboard"
        >
          <Settings className="w-5 h-5 text-gray-500 hover:text-purple-700" />
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
