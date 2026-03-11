import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tabs, TabsList, TabsTrigger, TabsContent,
} from "@/components/ui/tabs";
import {
  LayoutDashboard, FolderOpen, Clock, CheckCircle2, Users2, FileText, BarChart2, MessageCircle, BookOpen, CalendarClock, AlertTriangle, ThumbsUp, ShieldCheck, Settings, Award,
} from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, BarChart, Bar,
} from "recharts";
import { authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";
import { useTranslation } from "@/lib/useTranslation";
import HelpTooltip from "@/components/HelpTooltip";

// Chart color palette
const COLORS = [
  "#6366f1", "#22d3ee", "#4ade80", "#f59e42", "#a78bfa", "#f87171", "#f472b6", "#818cf8",
];

// --- Data Types ---
type Stats = {
  assigned: number; inProgress: number; completed: number; overdue: number; documents: number; approvals: number;
};
type StatusData = { name: string; value: number };
type Activity = { date: string; actions: number };
type Assignment = { id: string; title: string; status: string; updated: string };
type Review = { id: string; project: string; status: string; updated: string };
type Feedback = { id: string; message: string; from: string; date: string; sentiment: "positive"|"neutral"|"negative" };
type Comment = { id: string; content: string; doc: string; date: string };
type Deadline = { id: string; doc: string; due: string; daysLeft: number };
type DocType = { type: string; count: number };
type ErrorStat = { type: string; count: number };
type Collaborator = { name: string; role: string; projects: number };
type QualityMetrics = { avg_score: number; docs_with_scores: number; high_quality_count: number; needs_improvement_count: number };

export default function UserDashboardPage() {
  // Data State
  const [stats, setStats] = useState<Stats>({
    assigned: 0,
    inProgress: 0,
    completed: 0,
    overdue: 0,
    documents: 0,
    approvals: 0,
  });
  const [quality, setQuality] = useState<QualityMetrics | null>(null);
  const [statusData, setStatusData] = useState<StatusData[]>([]);
  const [activityData, setActivityData] = useState<Activity[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [docTypes, setDocTypes] = useState<DocType[]>([]);
  const [errorStats, setErrorStats] = useState<ErrorStat[]>([]);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [showPicker, setShowPicker] = useState(false);
  const username = useUserStore((s) => s.username);
  const { t } = useTranslation();

  // Dashboard Widget visibility state
  const DEFAULT_VISIBLE = ["kpi", "quality", "status", "activity", "assignments", "reviews", "deadlines", "feedback", "collaborators"];
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
    queryKey: ["user-dashboard"],
    queryFn: async () => {
      const r = await authenticatedFetch("/dashboard/user", {
        headers: username ? { "X-User": username } : undefined,
      });
      return r.ok ? r.json() : null;
    },
  });

  useEffect(() => {
    // Response is now { projects: [...], quality: {...} }
    const projects = data && Array.isArray(data.projects) ? data.projects : (Array.isArray(data) ? data : []);
    const qualityData = data && data.quality ? data.quality : null;

    if (projects.length > 0 || qualityData) {
      const docs = projects.reduce((t: number, p: any) => t + (p.docs ?? 0), 0);
      const approvals = projects.reduce((t: number, p: any) => t + (p.pending_approvals ?? 0), 0);
      const statusCounts = new Map<string, number>();
      const docTypeCounts = new Map<string, number>();
      projects.forEach((p: any) => {
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
      const completed =
        statusCounts.get("Complete") ?? statusCounts.get("Completed") ?? 0;
      const overdue = statusCounts.get("Overdue") ?? 0;
      setStats({
        assigned: projects.length,
        inProgress,
        completed,
        overdue,
        documents: docs,
        approvals,
      });
      setStatusData(
        Array.from(statusCounts.entries()).map(([name, value]) => ({
          name,
          value,
        })),
      );
      setDocTypes(
        Array.from(docTypeCounts.entries()).map(([type, count]) => ({
          type,
          count,
        })),
      );
      setActivityData([]);
      setAssignments([]);
      setReviews([]);
      setFeedbacks([]);
      setComments([]);
      setDeadlines([]);
      setErrorStats([]);
      setCollaborators([]);
      if (qualityData) {
        setQuality(qualityData);
      }
    } else if (isError) {
      setStats({
        assigned: 0,
        inProgress: 0,
        completed: 0,
        overdue: 0,
        documents: 0,
        approvals: 0,
      });
      setQuality(null);
      setStatusData([]);
      setActivityData([]);
      setAssignments([]);
      setReviews([]);
      setFeedbacks([]);
      setComments([]);
      setDeadlines([]);
      setErrorStats([]);
      setCollaborators([]);
      setDocTypes([]);
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
      key: "kpi", label: "Key Metrics", icon: LayoutDashboard,
      helpText: "Shows your assigned tasks, in-progress projects, completed work, and overdue items.",
      component: (
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Key Metrics</span>
            <HelpTooltip content="Shows your assigned tasks, in-progress projects, completed work, and overdue items." href="/help#kpi" />
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={Users2} label={t("dashboard.assigned")} value={stats.assigned} color="text-indigo-600" />
            <StatCard icon={Clock} label={t("dashboard.in_progress")} value={stats.inProgress} color="text-orange-600" />
            <StatCard icon={CheckCircle2} label={t("dashboard.completed")} value={stats.completed} color="text-emerald-600" />
            <StatCard icon={BarChart2} label={t("dashboard.overdue")} value={stats.overdue} color="text-red-600" />
          </div>
        </div>
      ),
    },
    {
      key: "quality", label: "Avg Quality Score", icon: Award,
      helpText: "Average ML-computed quality score across all documents you have access to. Scores above 80% are high quality; below 60% need improvement.",
      component: (
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <Award className={`w-10 h-10 ${quality ? qualityColor(quality.avg_score) : "text-gray-400"}`} />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className={`text-3xl font-bold leading-none ${quality ? qualityColor(quality.avg_score) : "text-gray-400"}`}>
                  {quality && quality.docs_with_scores > 0
                    ? `${Math.round(quality.avg_score * 100)}%`
                    : "—"}
                </p>
                <HelpTooltip
                  content="Average ML-computed quality score across all documents you have access to. Scores above 80% are high quality; below 60% need improvement."
                  href="/help#quality"
                />
              </div>
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
      key: "status", label: "My Project Status", icon: FolderOpen,
      helpText: "Breakdown of your projects by current status (In Progress, Complete, Overdue, etc.).",
      component: (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              My Project Status
              <HelpTooltip content="Breakdown of your projects by current status (In Progress, Complete, Overdue, etc.)." href="/help#status" />
            </CardTitle>
          </CardHeader>
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
      key: "activity", label: "My Recent Activity", icon: Clock,
      helpText: "Your document activity over the last 30 days — edits, uploads, approvals, and comments.",
      component: (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              My Recent Activity
              <HelpTooltip content="Your document activity over the last 30 days — edits, uploads, approvals, and comments." href="/help#activity" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
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
      key: "assignments", label: "My Assignments", icon: FileText,
      helpText: "Documents and review tasks that have been explicitly assigned to you, along with their current status.",
      component: (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              My Assignments
              <HelpTooltip content="Documents and review tasks that have been explicitly assigned to you, along with their current status." href="/help#assignments" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {assignments.map((a) => (
                <li key={a.id} className="flex justify-between items-center border-b last:border-none pb-2">
                  <span className="font-mono text-xs text-indigo-600">{a.id}</span>
                  <span className="flex-1 ml-4">{a.title}</span>
                  <span className={`rounded px-2 py-1 text-xs font-semibold
                    ${
                      a.status === "Completed"
                        ? "bg-emerald-100 text-emerald-700"
                        : a.status === "Overdue"
                          ? "bg-red-100 text-red-700"
                          : a.status === "In Progress"
                            ? "bg-orange-100 text-orange-700"
                            : "bg-indigo-100 text-indigo-700"
                    }`
                  }>
                    {a.status}
                  </span>
                  <span className="ml-4 text-gray-400 text-xs">{a.updated}</span>
                </li>
              ))}
              {assignments.length === 0 && (
                <li className="text-muted-foreground">No assignments found.</li>
              )}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "reviews", label: "My Reviews", icon: CheckCircle2,
      helpText: "Projects where you are listed as a reviewer, showing your review status and last update time.",
      component: (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              My Reviews
              <HelpTooltip content="Projects where you are listed as a reviewer, showing your review status and last update time." href="/help#reviews" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {reviews.map((r) => (
                <li key={r.id} className="flex justify-between items-center border-b last:border-none pb-2">
                  <span className="font-mono text-xs text-cyan-600">{r.id}</span>
                  <span className="flex-1 ml-4">{r.project}</span>
                  <span className={`rounded px-2 py-1 text-xs font-semibold
                    ${
                      r.status === "Approved"
                        ? "bg-emerald-100 text-emerald-700"
                        : r.status === "Pending"
                          ? "bg-orange-100 text-orange-700"
                          : "bg-indigo-100 text-indigo-700"
                    }`
                  }>
                    {r.status}
                  </span>
                  <span className="ml-4 text-gray-400 text-xs">{r.updated}</span>
                </li>
              ))}
              {reviews.length === 0 && (
                <li className="text-muted-foreground">No reviews found.</li>
              )}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "feedback", label: "My Feedback", icon: ThumbsUp,
      helpText: "Feedback items and kudos submitted on documents you own or are assigned to.",
      component: (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Feedback &amp; Kudos
              <HelpTooltip content="Feedback items and kudos submitted on documents you own or are assigned to." href="/help#feedback" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {feedbacks.map((f) => (
                <li key={f.id} className="flex gap-2 items-center border-b last:border-none pb-2">
                  <ThumbsUp className={
                    f.sentiment === "positive" ? "w-4 h-4 text-emerald-600" :
                    f.sentiment === "negative" ? "w-4 h-4 text-red-600" : "w-4 h-4 text-gray-600"
                  } />
                  <span>{f.message}</span>
                  <span className="ml-2 text-xs text-indigo-500">from {f.from}</span>
                  <span className="ml-auto text-xs text-gray-400">{f.date}</span>
                </li>
              ))}
              {feedbacks.length === 0 && <li className="text-muted-foreground">No feedback found.</li>}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "comments", label: "Recent Comments", icon: MessageCircle,
      component: (
        <Card>
          <CardHeader><CardTitle>Recent Comments on My Docs</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {comments.map((c) => (
                <li key={c.id} className="flex gap-2 items-center border-b last:border-none pb-2">
                  <MessageCircle className="w-4 h-4 text-cyan-500" />
                  <span className="flex-1">{c.content}</span>
                  <span className="text-xs text-indigo-600">{c.doc}</span>
                  <span className="ml-auto text-xs text-gray-400">{c.date}</span>
                </li>
              ))}
              {comments.length === 0 && <li className="text-muted-foreground">No comments found.</li>}
            </ul>
          </CardContent>
        </Card>
      ),
    },
    {
      key: "deadlines", label: "Upcoming Deadlines", icon: CalendarClock,
      helpText: "Documents with review deadlines approaching in the next 14 days, sorted by urgency.",
      component: (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Upcoming Deadlines
              <HelpTooltip content="Documents with review deadlines approaching in the next 14 days, sorted by urgency." href="/help#deadlines" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {deadlines.map((d) => (
                <li key={d.id} className="flex items-center gap-3">
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  <span className="font-bold">{d.doc}</span>
                  <span className="ml-2 text-red-500">Due {d.due}</span>
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
      key: "docTypes", label: "Docs by Type", icon: BookOpen,
      component: (
        <Card>
          <CardHeader><CardTitle>My Documents by Type</CardTitle></CardHeader>
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
      key: "errors", label: "Doc Quality Stats", icon: ShieldCheck,
      helpText: "Count of quality and formatting issues detected by the document checker across your documents.",
      component: (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Quality/Formatting Issues
              <HelpTooltip content="Count of quality and formatting issues detected by the document checker across your documents." href="/help#quality-stats" />
            </CardTitle>
          </CardHeader>
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
      key: "collaborators", label: "My Collaborators", icon: Users2,
      component: (
        <Card>
          <CardHeader><CardTitle>Frequent Collaborators</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {collaborators.map((c, i) => (
                <li key={c.name} className="flex gap-3 items-center">
                  <Users2 className="w-4 h-4 text-indigo-500" />
                  <span className="font-semibold">{c.name}</span>
                  <span className="text-xs text-gray-500">{c.role}</span>
                  <span className="ml-auto text-xs text-indigo-700">{c.projects} shared projects</span>
                </li>
              ))}
              {collaborators.length === 0 && (
                <li className="text-muted-foreground">No collaborators found.</li>
              )}
            </ul>
          </CardContent>
        </Card>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex gap-2 items-center">
          <LayoutDashboard className="w-7 h-7 text-indigo-600" /> {t("dashboard.title")}
        </h1>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setShowPicker((v) => !v)}
          title={t("dashboard.customize")}
          aria-label={t("dashboard.customize")}
        >
          <Settings className="w-5 h-5 text-gray-500 hover:text-indigo-600" />
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
