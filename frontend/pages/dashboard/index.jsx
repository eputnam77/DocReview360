import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ChatBot } from "@/components";
import { LayoutDashboard, Users2, CheckCircle2, Clock, BarChart2 } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, } from "recharts";
import { useDashboardVisibility } from "@/state/visibility";
import { authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";
// Color palette for charts
const COLORS = [
    "#6366f1", // Indigo
    "#22d3ee", // Cyan
    "#4ade80", // Green
    "#f59e42", // Orange
    "#a78bfa", // Purple
];
const LOG_LIMIT = 20;
function normalizeStatus(value) {
    if (typeof value !== "string") {
        return "";
    }
    return value.toLowerCase().replace(/[_-]/g, " ");
}
function isAssignedToUser(project, normalizedUser) {
    const directKeys = ["user", "owner", "assigned_to", "assignee", "assignedTo"];
    for (const key of directKeys) {
        const value = project[key];
        if (typeof value === "string" && value.toLowerCase() === normalizedUser) {
            return true;
        }
    }
    const listKeys = ["assignees", "assigned_users", "assignedTo"];
    for (const key of listKeys) {
        const value = project[key];
        if (Array.isArray(value) &&
            value.some((item) => typeof item === "string" && item.toLowerCase() === normalizedUser)) {
            return true;
        }
    }
    return false;
}
function extractDateString(value) {
    if (typeof value !== "string" || value.trim().length === 0) {
        return null;
    }
    const trimmed = value.trim();
    const direct = trimmed.slice(0, 10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(direct)) {
        return direct;
    }
    const parsed = new Date(trimmed);
    if (Number.isNaN(parsed.getTime())) {
        return null;
    }
    return parsed.toISOString().slice(0, 10);
}
function buildActivityData(projects) {
    const counts = new Map();
    const dateKeys = [
        "updated",
        "updated_at",
        "updatedAt",
        "modified",
        "modified_at",
        "last_updated",
        "lastUpdated",
    ];
    projects.forEach((project) => {
        for (const key of dateKeys) {
            const dateString = extractDateString(project[key]);
            if (dateString) {
                counts.set(dateString, (counts.get(dateString) ?? 0) + 1);
                break;
            }
        }
    });
    return Array.from(counts.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([date, actions]) => ({ date, actions }));
}
function computeDashboardData(projects, username) {
    const normalizedUser = typeof username === "string" ? username.toLowerCase() : "";
    const assignedCount = normalizedUser
        ? projects.filter((project) => isAssignedToUser(project, normalizedUser)).length
        : 0;
    let inProgress = 0;
    let completed = 0;
    let overdue = 0;
    projects.forEach((project) => {
        const normalizedStatus = normalizeStatus(project["status"] ??
            project["state"] ??
            project["phase_status"] ??
            project["workflow_status"] ??
            project["current_status"]);
        if (normalizedStatus.includes("progress")) {
            inProgress += 1;
        }
        if (normalizedStatus.includes("complete") || normalizedStatus.includes("done")) {
            completed += 1;
        }
        if (normalizedStatus.includes("overdue") || normalizedStatus.includes("late")) {
            overdue += 1;
        }
    });
    const stats = {
        assigned: assignedCount,
        inProgress,
        completed,
        overdue,
    };
    const statusData = [
        { name: "Assigned to Me", value: stats.assigned },
        { name: "In Progress", value: stats.inProgress },
        { name: "Completed", value: stats.completed },
        { name: "Overdue", value: stats.overdue },
    ];
    const activityData = buildActivityData(projects);
    return { stats, statusData, activityData };
}
export default function MainDashboardPage() {
    const [stats, setStats] = useState({
        assigned: 0,
        inProgress: 0,
        completed: 0,
        overdue: 0,
    });
    const [statusData, setStatusData] = useState([]);
    const [activityData, setActivityData] = useState([]);
    const [logs, setLogs] = useState([]);
    const [projectFilter, setProjectFilter] = useState(null);
    const { vis } = useDashboardVisibility();
    const username = useUserStore((s) => s.username);
    // Simulated API calls — replace with your own endpoints!
    useEffect(() => {
        let isActive = true;
        async function loadProjects() {
            try {
                const response = await authenticatedFetch("/projects");
                let payload = [];
                if (response.ok) {
                    try {
                        payload = await response.json();
                    }
                    catch {
                        payload = [];
                    }
                }
                const projects = Array.isArray(payload)
                    ? payload.filter((item) => item !== null && typeof item === "object")
                    : [];
                if (!isActive) {
                    return;
                }
                const { stats: computedStats, statusData, activityData } = computeDashboardData(projects, username);
                setStats(computedStats);
                setStatusData(statusData);
                setActivityData(activityData);
            }
            catch {
                if (!isActive) {
                    return;
                }
                setStats({ assigned: 0, inProgress: 0, completed: 0, overdue: 0 });
                setStatusData([]);
                setActivityData([]);
            }
        }
        async function loadLogs() {
            try {
                const response = await authenticatedFetch(`/logs?limit=${LOG_LIMIT}`);
                let payload = [];
                if (response.ok) {
                    try {
                        payload = await response.json();
                    }
                    catch {
                        payload = [];
                    }
                }
                const parsedLogs = Array.isArray(payload)
                    ? payload
                        .filter((entry) => entry !== null && typeof entry === "object")
                        .map((entry) => {
                        const timestamp = typeof entry.timestamp === "string" ? entry.timestamp : "";
                        const action = typeof entry.action === "string" ? entry.action : "";
                        const metadata = entry.metadata && typeof entry.metadata === "object"
                            ? entry.metadata
                            : undefined;
                        return { timestamp, action, metadata };
                    })
                        .filter((entry) => entry.timestamp && entry.action)
                    : [];
                if (!isActive) {
                    return;
                }
                setLogs(parsedLogs);
            }
            catch {
                if (!isActive) {
                    return;
                }
                setLogs([]);
            }
        }
        loadProjects();
        loadLogs();
        return () => {
            isActive = false;
        };
    }, [username]);
    // Unique projects for filter dropdown
    const projectOptions = Array.from(new Set(logs.map((l) => l.metadata?.project).filter(Boolean)));
    // KPI card helper
    const StatCard = ({ icon: Icon, label, value, color, }) => (<Card>
      <CardContent className="flex items-center gap-4 p-6">
        <Icon className={`w-10 h-10 ${color || "text-indigo-600"}`}/>
        <div>
          <p className="text-3xl font-bold leading-none">{value}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {label}
          </p>
        </div>
      </CardContent>
    </Card>);
    return (<div className="p-8 space-y-8">
      {/* Header */}
      <h1 className="text-3xl font-bold flex gap-2 items-center">
        <LayoutDashboard className="w-7 h-7 text-indigo-600"/> Dashboard
      </h1>

      {/* KPI Row */}
      {vis.stats && (<div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Users2} label="Assigned to Me" value={stats.assigned} color="text-indigo-600"/>
        <StatCard icon={Clock} label="In Progress" value={stats.inProgress} color="text-orange-600"/>
        <StatCard icon={CheckCircle2} label="Completed" value={stats.completed} color="text-emerald-600"/>
        <StatCard icon={BarChart2} label="Overdue" value={stats.overdue} color="text-red-600"/>
      </div>)}

      {/* Visuals */}
      <div className="grid gap-8 md:grid-cols-2">
        {/* Pie Chart: Project Status */}
        {vis.status && (<Card>
          <CardHeader>
            <CardTitle>Project Status</CardTitle>
          </CardHeader>
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
        </Card>)}
        {/* Line Chart: Activity */}
        {vis.activity && (<Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={activityData}>
                <XAxis dataKey="date"/>
                <YAxis allowDecimals={false}/>
                <Tooltip />
                <Line type="monotone" dataKey="actions" stroke="#6366f1" strokeWidth={2}/>
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>)}
      </div>

      {/* Feed and Tabs */}
      {vis.logs && (<Tabs defaultValue="projects" className="mt-6 space-y-4">
        <TabsList>
          <TabsTrigger value="projects">Project Feed</TabsTrigger>
          <TabsTrigger value="activity">Activity Feed</TabsTrigger>
        </TabsList>
        <TabsContent value="projects">
          <Card>
            <CardContent className="h-64 overflow-y-auto rounded-lg bg-gray-50 dark:bg-gray-900 p-4">
              <select className="mb-2 border rounded p-1" value={projectFilter ?? ""} onChange={(e) => setProjectFilter(e.target.value || null)}>
                <option value="">All projects</option>
                {projectOptions.map((id) => (<option key={id} value={id}>
                    {id}
                  </option>))}
              </select>
              <ul className="text-sm space-y-1">
                {logs
                .filter((l) => !projectFilter || l.metadata?.project === projectFilter)
                .map((l, i) => (<li key={i}>
                      <span className="inline-block w-24 text-gray-400">
                        {l.timestamp.slice(0, 10)}
                      </span>
                      <span className="ml-2">{l.action}</span>
                    </li>))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="activity">
          <Card>
            <CardContent className="h-64 flex items-center justify-center rounded-lg bg-gray-50 dark:bg-gray-900">
              <BarChart2 className="w-16 h-16 text-gray-400"/>
              <span className="ml-4 text-gray-500 dark:text-gray-400">
                (Replace with a stacked bar or detailed feed as needed.)
              </span>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>)}
      {/* Simple project chatbot */}
      <ChatBot />
    </div>);
}
