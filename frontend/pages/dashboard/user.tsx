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
  Clock,
  CheckCircle2,
  Users2,
  FileText,
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

// Chart color palette
const COLORS = [
  "#6366f1", // Indigo
  "#22d3ee", // Cyan
  "#4ade80", // Green
  "#f59e42", // Orange
  "#a78bfa", // Purple
  "#f87171", // Red
];

type Stats = {
  assigned: number;
  inProgress: number;
  completed: number;
  overdue: number;
  documents: number;
  approvals: number;
};
type StatusData = { name: string; value: number };
type Activity = { date: string; actions: number };
type Assignment = { id: string; title: string; status: string; updated: string };
type Review = { id: string; project: string; status: string; updated: string };

export default function UserDashboardPage() {
  // Simulated user data – replace with actual user context or API!
  const [stats, setStats] = useState<Stats>({
    assigned: 4,
    inProgress: 2,
    completed: 7,
    overdue: 1,
    documents: 12,
    approvals: 3,
  });
  const [statusData, setStatusData] = useState<StatusData[]>([]);
  const [activityData, setActivityData] = useState<Activity[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);

  useEffect(() => {
    // KPIs
    setStats({
      assigned: 4,
      inProgress: 2,
      completed: 7,
      overdue: 1,
      documents: 12,
      approvals: 3,
    });
    // Status chart
    setStatusData([
      { name: "Assigned", value: 4 },
      { name: "In Progress", value: 2 },
      { name: "Completed", value: 7 },
      { name: "Overdue", value: 1 },
    ]);
    // Line chart: user activity
    setActivityData([
      { date: "2025-07-01", actions: 1 },
      { date: "2025-07-02", actions: 3 },
      { date: "2025-07-03", actions: 2 },
      { date: "2025-07-04", actions: 4 },
      { date: "2025-07-05", actions: 2 },
    ]);
    // Assignments list
    setAssignments([
      { id: "AC-101", title: "Policy Update", status: "In Progress", updated: "2025-07-04" },
      { id: "AC-102", title: "Compliance Review", status: "Completed", updated: "2025-07-02" },
      { id: "AC-103", title: "Draft SOP", status: "Assigned", updated: "2025-07-01" },
      { id: "AC-104", title: "Incident Report", status: "Overdue", updated: "2025-07-03" },
    ]);
    // Reviews list
    setReviews([
      { id: "R-201", project: "AC-101", status: "Pending", updated: "2025-07-04" },
      { id: "R-202", project: "AC-103", status: "Approved", updated: "2025-07-02" },
    ]);
  }, []);

  // KPI Card helper
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
        <LayoutDashboard className="w-7 h-7 text-indigo-600" /> My Dashboard
      </h1>

      {/* KPIs */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Users2} label="Assigned" value={stats.assigned} color="text-indigo-600" />
        <StatCard icon={Clock} label="In Progress" value={stats.inProgress} color="text-orange-600" />
        <StatCard icon={CheckCircle2} label="Completed" value={stats.completed} color="text-emerald-600" />
        <StatCard icon={BarChart2} label="Overdue" value={stats.overdue} color="text-red-600" />
      </div>

      {/* Visuals */}
      <div className="grid gap-8 md:grid-cols-2">
        {/* Pie Chart: Status */}
        <Card>
          <CardHeader>
            <CardTitle>My Project Status</CardTitle>
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
        {/* Line Chart: User Activity */}
        <Card>
          <CardHeader>
            <CardTitle>My Recent Activity</CardTitle>
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
      </div>

      {/* Assignments & Reviews */}
      <Tabs defaultValue="assignments" className="mt-6 space-y-4">
        <TabsList>
          <TabsTrigger value="assignments">My Assignments</TabsTrigger>
          <TabsTrigger value="reviews">My Reviews</TabsTrigger>
        </TabsList>
        <TabsContent value="assignments">
          <Card>
            <CardHeader>
              <CardTitle>Assigned Projects</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {assignments.map((a) => (
                  <li
                    key={a.id}
                    className="flex justify-between items-center border-b last:border-none pb-2"
                  >
                    <span className="font-mono text-xs text-indigo-600">
                      {a.id}
                    </span>
                    <span className="flex-1 ml-4">{a.title}</span>
                    <span className={`rounded px-2 py-1 text-xs font-semibold
                      ${a.status === "Completed"
                        ? "bg-emerald-100 text-emerald-700"
                        : a.status === "Overdue"
                        ? "bg-red-100 text-red-700"
                        : a.status === "In Progress"
                        ? "bg-orange-100 text-orange-700"
                        : "bg-indigo-100 text-indigo-700"
                      }`}
                    >
                      {a.status}
                    </span>
                    <span className="ml-4 text-gray-400 text-xs">
                      {a.updated}
                    </span>
                  </li>
                ))}
                {assignments.length === 0 && (
                  <li className="text-muted-foreground">No assignments found.</li>
                )}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="reviews">
          <Card>
            <CardHeader>
              <CardTitle>My Reviews</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {reviews.map((r) => (
                  <li
                    key={r.id}
                    className="flex justify-between items-center border-b last:border-none pb-2"
                  >
                    <span className="font-mono text-xs text-cyan-600">
                      {r.id}
                    </span>
                    <span className="flex-1 ml-4">{r.project}</span>
                    <span className={`rounded px-2 py-1 text-xs font-semibold
                      ${r.status === "Approved"
                        ? "bg-emerald-100 text-emerald-700"
                        : r.status === "Pending"
                        ? "bg-orange-100 text-orange-700"
                        : "bg-indigo-100 text-indigo-700"
                      }`}
                    >
                      {r.status}
                    </span>
                    <span className="ml-4 text-gray-400 text-xs">
                      {r.updated}
                    </span>
                  </li>
                ))}
                {reviews.length === 0 && (
                  <li className="text-muted-foreground">No reviews found.</li>
                )}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

