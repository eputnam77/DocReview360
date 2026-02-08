import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LayoutDashboard, FolderOpen, Clock, CheckCircle2, Users2, FileText, BarChart2, MessageCircle, BookOpen, CalendarClock, AlertTriangle, ThumbsUp, ShieldCheck, } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, BarChart, Bar, } from "recharts";
import { authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";
// Chart color palette
const COLORS = [
    "#6366f1", "#22d3ee", "#4ade80", "#f59e42", "#a78bfa", "#f87171", "#f472b6", "#818cf8",
];
export default function UserDashboardPage() {
    // Data State
    const [stats, setStats] = useState({ assigned: 4, inProgress: 2, completed: 7, overdue: 1, documents: 12, approvals: 3 });
    const [statusData, setStatusData] = useState([]);
    const [activityData, setActivityData] = useState([]);
    const [assignments, setAssignments] = useState([]);
    const [reviews, setReviews] = useState([]);
    const [feedbacks, setFeedbacks] = useState([]);
    const [comments, setComments] = useState([]);
    const [deadlines, setDeadlines] = useState([]);
    const [docTypes, setDocTypes] = useState([]);
    const [errorStats, setErrorStats] = useState([]);
    const [collaborators, setCollaborators] = useState([]);
    const [showPicker, setShowPicker] = useState(false);
    const username = useUserStore((s) => s.username);
    // Dashboard Widget visibility state
    const DASHBOARD_KEYS = [
        "kpi", "status", "activity", "assignments", "reviews", "feedback", "comments", "deadlines", "docTypes", "errors", "collaborators",
    ];
    const DEFAULT_VISIBLE = ["kpi", "status", "activity", "assignments", "reviews", "deadlines", "feedback", "collaborators"];
    const [visibleDashboards, setVisibleDashboards] = useState(DEFAULT_VISIBLE);
    useEffect(() => {
        if (typeof window !== "undefined") {
            const stored = localStorage.getItem("visibleUserDashboards");
            if (stored) {
                try {
                    const parsed = JSON.parse(stored);
                    if (Array.isArray(parsed)) {
                        setVisibleDashboards(parsed);
                    }
                }
                catch {
                    // ignore malformed localStorage
                }
            }
        }
    }, []);
    const toggleDashboard = (key) => {
        setVisibleDashboards((prev) => {
            const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
            localStorage.setItem("visibleUserDashboards", JSON.stringify(next));
            return next;
        });
    };
    const fallback = {
        stats: { assigned: 4, inProgress: 2, completed: 7, overdue: 1, documents: 12, approvals: 3 },
        status: [
            { name: "Assigned", value: 4 },
            { name: "In Progress", value: 2 },
            { name: "Completed", value: 7 },
            { name: "Overdue", value: 1 },
        ],
        activity: [
            { date: "2025-07-01", actions: 1 },
            { date: "2025-07-02", actions: 3 },
            { date: "2025-07-03", actions: 2 },
            { date: "2025-07-04", actions: 4 },
            { date: "2025-07-05", actions: 2 },
        ],
        assignments: [
            { id: "AC-101", title: "Policy Update", status: "In Progress", updated: "2025-07-04" },
            { id: "AC-102", title: "Compliance Review", status: "Completed", updated: "2025-07-02" },
            { id: "AC-103", title: "Draft SOP", status: "Assigned", updated: "2025-07-01" },
            { id: "AC-104", title: "Incident Report", status: "Overdue", updated: "2025-07-03" },
        ],
        reviews: [
            { id: "R-201", project: "AC-101", status: "Pending", updated: "2025-07-04" },
            { id: "R-202", project: "AC-103", status: "Approved", updated: "2025-07-02" },
        ],
        feedbacks: [
            { id: "F-01", message: "Great summary section!", from: "Team Lead", date: "2025-07-02", sentiment: "positive" },
            { id: "F-02", message: "Missing some regulatory context.", from: "SME", date: "2025-07-03", sentiment: "neutral" },
            { id: "F-03", message: "Formatting issues found.", from: "Reviewer", date: "2025-07-04", sentiment: "negative" },
        ],
        comments: [
            { id: "C-01", content: "Clarify para 2.2 for non-native speakers.", doc: "AC-101", date: "2025-07-02" },
            { id: "C-02", content: "Need to update references.", doc: "AC-103", date: "2025-07-03" },
        ],
        deadlines: [
            { id: "AC-101", doc: "Policy Update", due: "2025-07-07", daysLeft: 3 },
            { id: "AC-104", doc: "Incident Report", due: "2025-07-09", daysLeft: 5 },
        ],
        docTypes: [
            { type: "AC", count: 5 },
            { type: "Order", count: 3 },
            { type: "Memo", count: 2 },
            { type: "TSO", count: 1 },
            { type: "Other", count: 1 },
        ],
        errors: [
            { type: "Formatting", count: 2 },
            { type: "Headings", count: 1 },
            { type: "Acronyms", count: 1 },
            { type: "Accessibility", count: 1 },
        ],
        collaborators: [
            { name: "Jane Doe", role: "Tech Writer", projects: 3 },
            { name: "John Smith", role: "SME", projects: 2 },
            { name: "Alice Lee", role: "Reviewer", projects: 2 },
        ],
    };
    const { data, isError } = useQuery({
        queryKey: ["user-dashboard"],
        queryFn: async () => {
            const r = await authenticatedFetch("/dashboard/user", {
                headers: username ? { "X-User": username } : undefined,
            });
            return r.ok ? r.json() : null;
        },
    });
    useEffect(() => {
        if (Array.isArray(data) && data.length > 0) {
            const docs = data.reduce((t, p) => t + (p.docs ?? 0), 0);
            const approvals = data.reduce((t, p) => t + (p.pending_approvals ?? 0), 0);
            setStats({
                assigned: data.length,
                inProgress: data.filter((p) => p.phase !== "done").length,
                completed: data.filter((p) => p.phase === "done").length,
                overdue: fallback.stats.overdue,
                documents: docs,
                approvals,
            });
        }
        else if (isError) {
            setStats(fallback.stats);
            setStatusData(fallback.status);
            setActivityData(fallback.activity);
            setAssignments(fallback.assignments);
            setReviews(fallback.reviews);
            setFeedbacks(fallback.feedbacks);
            setComments(fallback.comments);
            setDeadlines(fallback.deadlines);
            setDocTypes(fallback.docTypes);
            setErrorStats(fallback.errors);
            setCollaborators(fallback.collaborators);
        }
    }, [data, isError]);
    // KPI Card
    const StatCard = ({ icon: Icon, label, value, color, }) => (<Card>
      <CardContent className="flex items-center gap-4 p-6">
        <Icon className={`w-10 h-10 ${color || "text-indigo-600"}`}/>
        <div>
          <p className="text-3xl font-bold leading-none">{value}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{label}</p>
        </div>
      </CardContent>
    </Card>);
    // Dashboard Registry
    const DASHBOARDS = [
        {
            key: "kpi", label: "Key Metrics", icon: LayoutDashboard,
            component: (<div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={Users2} label="Assigned" value={stats.assigned} color="text-indigo-600"/>
          <StatCard icon={Clock} label="In Progress" value={stats.inProgress} color="text-orange-600"/>
          <StatCard icon={CheckCircle2} label="Completed" value={stats.completed} color="text-emerald-600"/>
          <StatCard icon={BarChart2} label="Overdue" value={stats.overdue} color="text-red-600"/>
        </div>),
        },
        {
            key: "status", label: "My Project Status", icon: FolderOpen,
            component: (<Card>
          <CardHeader><CardTitle>My Project Status</CardTitle></CardHeader>
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
            key: "activity", label: "My Recent Activity", icon: Clock,
            component: (<Card>
          <CardHeader><CardTitle>My Recent Activity</CardTitle></CardHeader>
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
        </Card>),
        },
        {
            key: "assignments", label: "My Assignments", icon: FileText,
            component: (<Card>
          <CardHeader><CardTitle>My Assignments</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {assignments.map((a) => (<li key={a.id} className="flex justify-between items-center border-b last:border-none pb-2">
                  <span className="font-mono text-xs text-indigo-600">{a.id}</span>
                  <span className="flex-1 ml-4">{a.title}</span>
                  <span className={`rounded px-2 py-1 text-xs font-semibold
                    ${a.status === "Completed"
                        ? "bg-emerald-100 text-emerald-700"
                        : a.status === "Overdue"
                            ? "bg-red-100 text-red-700"
                            : a.status === "In Progress"
                                ? "bg-orange-100 text-orange-700"
                                : "bg-indigo-100 text-indigo-700"}`}>
                    {a.status}
                  </span>
                  <span className="ml-4 text-gray-400 text-xs">{a.updated}</span>
                </li>))}
              {assignments.length === 0 && (<li className="text-muted-foreground">No assignments found.</li>)}
            </ul>
          </CardContent>
        </Card>),
        },
        {
            key: "reviews", label: "My Reviews", icon: CheckCircle2,
            component: (<Card>
          <CardHeader><CardTitle>My Reviews</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {reviews.map((r) => (<li key={r.id} className="flex justify-between items-center border-b last:border-none pb-2">
                  <span className="font-mono text-xs text-cyan-600">{r.id}</span>
                  <span className="flex-1 ml-4">{r.project}</span>
                  <span className={`rounded px-2 py-1 text-xs font-semibold
                    ${r.status === "Approved"
                        ? "bg-emerald-100 text-emerald-700"
                        : r.status === "Pending"
                            ? "bg-orange-100 text-orange-700"
                            : "bg-indigo-100 text-indigo-700"}`}>
                    {r.status}
                  </span>
                  <span className="ml-4 text-gray-400 text-xs">{r.updated}</span>
                </li>))}
              {reviews.length === 0 && (<li className="text-muted-foreground">No reviews found.</li>)}
            </ul>
          </CardContent>
        </Card>),
        },
        {
            key: "feedback", label: "My Feedback", icon: ThumbsUp,
            component: (<Card>
          <CardHeader><CardTitle>Feedback & Kudos</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {feedbacks.map((f) => (<li key={f.id} className="flex gap-2 items-center border-b last:border-none pb-2">
                  <ThumbsUp className={f.sentiment === "positive" ? "w-4 h-4 text-emerald-600" :
                        f.sentiment === "negative" ? "w-4 h-4 text-red-600" : "w-4 h-4 text-gray-600"}/>
                  <span>{f.message}</span>
                  <span className="ml-2 text-xs text-indigo-500">from {f.from}</span>
                  <span className="ml-auto text-xs text-gray-400">{f.date}</span>
                </li>))}
              {feedbacks.length === 0 && <li className="text-muted-foreground">No feedback found.</li>}
            </ul>
          </CardContent>
        </Card>),
        },
        {
            key: "comments", label: "Recent Comments", icon: MessageCircle,
            component: (<Card>
          <CardHeader><CardTitle>Recent Comments on My Docs</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {comments.map((c) => (<li key={c.id} className="flex gap-2 items-center border-b last:border-none pb-2">
                  <MessageCircle className="w-4 h-4 text-cyan-500"/>
                  <span className="flex-1">{c.content}</span>
                  <span className="text-xs text-indigo-600">{c.doc}</span>
                  <span className="ml-auto text-xs text-gray-400">{c.date}</span>
                </li>))}
              {comments.length === 0 && <li className="text-muted-foreground">No comments found.</li>}
            </ul>
          </CardContent>
        </Card>),
        },
        {
            key: "deadlines", label: "Upcoming Deadlines", icon: CalendarClock,
            component: (<Card>
          <CardHeader><CardTitle>Upcoming Deadlines</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {deadlines.map((d) => (<li key={d.id} className="flex items-center gap-3">
                  <AlertTriangle className="w-4 h-4 text-yellow-600"/>
                  <span className="font-bold">{d.doc}</span>
                  <span className="ml-2 text-red-500">Due {d.due}</span>
                  <span className="ml-auto text-xs text-gray-500">{d.daysLeft} days left</span>
                </li>))}
              {deadlines.length === 0 && <li>No upcoming deadlines.</li>}
            </ul>
          </CardContent>
        </Card>),
        },
        {
            key: "docTypes", label: "Docs by Type", icon: BookOpen,
            component: (<Card>
          <CardHeader><CardTitle>My Documents by Type</CardTitle></CardHeader>
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
            key: "errors", label: "Doc Quality Stats", icon: ShieldCheck,
            component: (<Card>
          <CardHeader><CardTitle>Quality/Formatting Issues</CardTitle></CardHeader>
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
            key: "collaborators", label: "My Collaborators", icon: Users2,
            component: (<Card>
          <CardHeader><CardTitle>Frequent Collaborators</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {collaborators.map((c, i) => (<li key={c.name} className="flex gap-3 items-center">
                  <Users2 className="w-4 h-4 text-indigo-500"/>
                  <span className="font-semibold">{c.name}</span>
                  <span className="text-xs text-gray-500">{c.role}</span>
                  <span className="ml-auto text-xs text-indigo-700">{c.projects} shared projects</span>
                </li>))}
              {collaborators.length === 0 && (<li className="text-muted-foreground">No collaborators found.</li>)}
            </ul>
          </CardContent>
        </Card>),
        },
    ];
    return (<div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex gap-2 items-center">
          <LayoutDashboard className="w-7 h-7 text-indigo-600"/> My Dashboard
        </h1>
        <Button variant="outline" size="sm" onClick={() => setShowPicker((v) => !v)}>
          Customize Dashboard
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
