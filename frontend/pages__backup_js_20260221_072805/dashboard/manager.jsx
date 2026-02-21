import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent, } from "@/components/ui/tabs";
import { LayoutDashboard, FolderOpen, FileText, Users2, Clock, BarChart2, ShieldCheck, CalendarClock, AlertTriangle, PieChart as PieChartIcon, TrendingUp, UserCheck, BookOpen, CheckCircle2, } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, } from "recharts";
import { authenticatedFetch } from "@/lib/api";
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
// --- Main Component ---
export default function ManagerDashboardPage() {
    // --- Data State ---
    const [stats, setStats] = useState({
        projects: 0, users: 0, documents: 0, approvals: 0,
        inProgress: 0, completed: 0, overdue: 0, active: 0,
    });
    const [statusData, setStatusData] = useState([]);
    const [userLeaderboard, setUserLeaderboard] = useState([]);
    const [activityData, setActivityData] = useState([]);
    const [logs, setLogs] = useState([]);
    const [deadlines, setDeadlines] = useState([]);
    const [errorStats, setErrorStats] = useState([]);
    const [turnarounds, setTurnarounds] = useState([]);
    const [docTypes, setDocTypes] = useState([]);
    const [reviewStats, setReviewStats] = useState([]);
    const [showPicker, setShowPicker] = useState(false);
    // --- Customizable dashboard visibility state ---
    const DASHBOARD_KEYS = [
        "kpi", "status", "leaderboard", "activity", "deadlines", "reviews", "errors", "turnaround", "docTypes", "logs",
    ];
    const DEFAULT_VISIBLE = ["kpi", "status", "leaderboard", "activity", "deadlines", "reviews", "logs"];
    // Initialize with a stable value for SSR; hydrate from localStorage after mount
    const [visibleDashboards, setVisibleDashboards] = useState(DEFAULT_VISIBLE);
    useEffect(() => {
        try {
            if (typeof window !== "undefined") {
                const stored = localStorage.getItem("visibleDashboards");
                if (stored)
                    setVisibleDashboards(JSON.parse(stored));
            }
        }
        catch {
            // ignore JSON/localStorage errors
        }
    }, []);
    const toggleDashboard = (key) => {
        setVisibleDashboards((prev) => {
            const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
            localStorage.setItem("visibleDashboards", JSON.stringify(next));
            return next;
        });
    };
    const { data, isError } = useQuery({
        queryKey: ["manager-dashboard"],
        queryFn: async () => {
            const r = await authenticatedFetch("/dashboard/manager");
            return r.ok ? r.json() : null;
        },
    });
    useEffect(() => {
        if (data) {
            const projects = Array.isArray(data.projects) ? data.projects : [];
            const docs = projects.reduce((t, p) => t + (p.docs ?? 0), 0);
            const approvals = projects.reduce((t, p) => t + (p.pending_approvals ?? 0), 0);
            const statusCounts = new Map();
            const docTypeCounts = new Map();
            projects.forEach((p) => {
                const status = typeof p.status === "string" && p.status.trim()
                    ? p.status
                    : "Unknown";
                statusCounts.set(status, (statusCounts.get(status) ?? 0) + 1);
                const docType = typeof p.doc_type === "string" && p.doc_type.trim()
                    ? p.doc_type
                    : "Unknown";
                docTypeCounts.set(docType, (docTypeCounts.get(docType) ?? 0) + 1);
            });
            const inProgress = statusCounts.get("In Progress") ?? 0;
            const completed = (statusCounts.get("Complete") ?? statusCounts.get("Completed") ?? 0);
            const overdue = statusCounts.get("Overdue") ?? 0;
            const workload = data.workload && typeof data.workload === "object" ? data.workload : {};
            setStats({
                projects: projects.length,
                users: Object.keys(workload).length,
                documents: docs,
                approvals,
                inProgress,
                completed,
                overdue,
                active: projects.filter((p) => p.pending_approvals > 0).length,
            });
            setStatusData(Array.from(statusCounts.entries()).map(([name, value]) => ({
                name,
                value,
            })));
            setUserLeaderboard(Object.entries(workload).map(([user, count]) => ({ user, projects: count })));
            setDocTypes(Array.from(docTypeCounts.entries()).map(([type, count]) => ({ type, count })));
            setActivityData([]);
            setLogs([]);
            setDeadlines([]);
            setErrorStats([]);
            setTurnarounds([]);
            setReviewStats([]);
        }
        else if (isError) {
            setStats({
                projects: 0,
                users: 0,
                documents: 0,
                approvals: 0,
                inProgress: 0,
                completed: 0,
                overdue: 0,
                active: 0,
            });
            setStatusData([]);
            setUserLeaderboard([]);
            setActivityData([]);
            setLogs([]);
            setDeadlines([]);
            setErrorStats([]);
            setTurnarounds([]);
            setDocTypes([]);
            setReviewStats([]);
        }
    }, [data, isError]);
    // --- KPI Card ---
    const StatCard = ({ icon: Icon, label, value, color, }) => (<Card>
      <CardContent className="flex items-center gap-4 p-6">
        <Icon className={`w-10 h-10 ${color || "text-indigo-600"}`}/>
        <div>
          <p className="text-3xl font-bold leading-none">{value}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{label}</p>
        </div>
      </CardContent>
    </Card>);
    // --- Dashboard Widget Registry ---
    const DASHBOARDS = [
        {
            key: "kpi",
            label: "Key Performance Indicators",
            icon: LayoutDashboard,
            component: (<div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={FolderOpen} label="Projects" value={stats.projects} color="text-indigo-600"/>
          <StatCard icon={Users2} label="Users" value={stats.users} color="text-emerald-600"/>
          <StatCard icon={FileText} label="Documents" value={stats.documents} color="text-cyan-600"/>
          <StatCard icon={Clock} label="Active Workflows" value={stats.active} color="text-yellow-600"/>
        </div>),
        },
        {
            key: "status",
            label: "Project Status Breakdown",
            icon: PieChartIcon,
            component: (<Card>
          <CardHeader><CardTitle>Project Status Breakdown</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${name}: ${value}`}>
                  {statusData.map((entry, idx) => (<Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]}/>))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>),
        },
        {
            key: "leaderboard",
            label: "User/Team Leaderboard",
            icon: BarChart2,
            component: (<Card>
          <CardHeader><CardTitle>User/Team Leaderboard</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={userLeaderboard}>
                <XAxis dataKey="user"/>
                <YAxis allowDecimals={false}/>
                <Tooltip />
                <Bar dataKey="projects" fill="#6366f1"/>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>),
        },
        {
            key: "activity",
            label: "System Activity",
            icon: TrendingUp,
            component: (<Card>
          <CardHeader><CardTitle>System Activity (Last 5 Days)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={activityData}>
                <XAxis dataKey="date"/>
                <YAxis allowDecimals={false}/>
                <Tooltip />
                <Bar dataKey="actions" fill="#f59e42"/>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>),
        },
        {
            key: "deadlines",
            label: "Upcoming Deadlines",
            icon: CalendarClock,
            component: (<Card>
          <CardHeader><CardTitle>Upcoming Deadlines (next 7 days)</CardTitle></CardHeader>
          <CardContent>
            <ul className="text-sm space-y-2">
              {deadlines.map((d, i) => (<li key={i} className="flex items-center gap-3">
                  <AlertTriangle className="w-4 h-4 text-yellow-600"/>
                  <span className="font-bold">{d.project}</span>
                  <span>due <span className="text-red-500">{d.due}</span></span>
                  <span className="ml-2 text-indigo-700">@{d.user}</span>
                  <span className="ml-auto text-xs text-gray-500">{d.daysLeft} days left</span>
                </li>))}
              {deadlines.length === 0 && <li>No upcoming deadlines.</li>}
            </ul>
          </CardContent>
        </Card>),
        },
        {
            key: "reviews",
            label: "Pending Reviews",
            icon: UserCheck,
            component: (<Card>
          <CardHeader><CardTitle>Pending Reviews by User</CardTitle></CardHeader>
          <CardContent>
            <ul className="text-sm space-y-2">
              {reviewStats.map((r, i) => (<li key={i} className="flex items-center gap-3">
                  <CheckCircle2 className="w-4 h-4 text-cyan-600"/>
                  <span className="font-bold">{r.reviewer}</span>
                  <span className="ml-2 text-amber-700">{r.pending} pending</span>
                </li>))}
              {reviewStats.length === 0 && <li>All reviews up to date.</li>}
            </ul>
          </CardContent>
        </Card>),
        },
        {
            key: "errors",
            label: "Quality/Error Stats",
            icon: AlertTriangle,
            component: (<Card>
          <CardHeader><CardTitle>Top Quality/Formatting Issues</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={errorStats}>
                <XAxis dataKey="type"/>
                <YAxis allowDecimals={false}/>
                <Tooltip />
                <Bar dataKey="count" fill="#f87171"/>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>),
        },
        {
            key: "turnaround",
            label: "Turnaround Times",
            icon: Clock,
            component: (<Card>
          <CardHeader><CardTitle>Average Turnaround Time (days per phase)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={turnarounds}>
                <XAxis dataKey="phase"/>
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="avgDays" stroke="#4ade80"/>
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>),
        },
        {
            key: "docTypes",
            label: "Document Type Breakdown",
            icon: BookOpen,
            component: (<Card>
          <CardHeader><CardTitle>Document Type Breakdown</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={docTypes} dataKey="count" nameKey="type" cx="50%" cy="50%" outerRadius={80} label={({ type, count }) => `${type}: ${count}`}>
                  {docTypes.map((entry, idx) => (<Cell key={`cell-doc-${idx}`} fill={COLORS[idx % COLORS.length]}/>))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>),
        },
        {
            key: "logs",
            label: "Audit/Activity Feed",
            icon: ShieldCheck,
            component: (<Tabs defaultValue="logs" className="mt-2 space-y-2">
          <TabsList>
            <TabsTrigger value="logs">Recent Activity</TabsTrigger>
            <TabsTrigger value="users">Top Users</TabsTrigger>
          </TabsList>
          <TabsContent value="logs">
            <Card>
              <CardHeader><CardTitle>Audit Feed</CardTitle></CardHeader>
              <CardContent className="max-h-64 overflow-y-auto">
                <ul className="text-sm space-y-1">
                  {logs.map((l, i) => (<li key={i} className="flex gap-2">
                      <span className="inline-block w-24 text-gray-400">{l.timestamp.slice(0, 10)}</span>
                      <span className="font-medium">{l.action}</span>
                      {l.metadata?.user && <span className="ml-2 text-indigo-600">@{l.metadata.user}</span>}
                      {l.metadata?.project && <span className="ml-2 text-teal-600">{l.metadata.project}</span>}
                    </li>))}
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
                  {userLeaderboard.map((u, idx) => (<li key={u.user} className="flex items-center gap-2">
                      <span className="font-semibold">{idx + 1}.</span>
                      <span className="flex-1">{u.user}</span>
                      <span className="text-indigo-700">{u.projects} projects</span>
                    </li>))}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>),
        },
    ];
    // --- Render ---
    return (<div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex gap-2 items-center">
          <ShieldCheck className="w-7 h-7 text-purple-700"/>
          Manager & Senior TW Dashboard
        </h1>
        <Button variant="outline" size="sm" onClick={() => setShowPicker((v) => !v)}>
          Customize Dashboards
        </Button>
      </div>
      {/* Picker Modal */}
      {showPicker && (<div className="fixed left-0 top-0 w-full h-full bg-black bg-opacity-40 z-40 flex justify-center items-center">
          <div className="bg-white dark:bg-gray-900 shadow-2xl rounded-lg p-6 w-96">
            <h3 className="font-bold mb-2 flex gap-2 items-center">
              <LayoutDashboard className="w-5 h-5"/>
              Select dashboards to show
            </h3>
            <div className="space-y-2">
              {DASHBOARDS.map((db) => (<label key={db.key} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={visibleDashboards.includes(db.key)} onChange={() => toggleDashboard(db.key)}/>
                  <db.icon className="w-4 h-4"/>
                  <span>{db.label}</span>
                </label>))}
            </div>
            <div className="flex justify-end mt-4">
              <Button onClick={() => setShowPicker(false)} size="sm">
                Done
              </Button>
            </div>
          </div>
        </div>)}
      {/* Main Dashboard Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {DASHBOARDS.filter((db) => visibleDashboards.includes(db.key)).map((db) => (<div key={db.key}>{db.component}</div>))}
      </div>
    </div>);
}
