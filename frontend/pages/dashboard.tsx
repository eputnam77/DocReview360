import React, { useEffect, useState } from "react";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { LayoutDashboard, FolderOpen, FileText, Users2, BarChart2 } from "lucide-react";

/**
 * DashboardsPage – high‑level KPIs with placeholder charts.
 * Drop into your routes as <DashboardsPage />.
 */
export default function DashboardsPage() {
  const [stats, setStats] = useState({
    projects: 0,
    documents: 0,
    workflows: 0,
    approvals: 0,
  });
  const [logs, setLogs] = useState<any[]>([]);
  const [projectFilter, setProjectFilter] = useState<string | null>(null);

  useEffect(() => {
    fetch("/metrics/summary")
      .then((r) => r.json())
      .then(setStats)
      .catch(() =>
        setStats({ projects: 0, documents: 0, workflows: 0, approvals: 0 })
      );
    fetch("/api/audit")
      .then((r) => r.json())
      .then(setLogs)
      .catch(() => setLogs([]));
  }, []);

  const StatCard = ({ icon: Icon, label, value }: { icon: any; label: string; value: number }) => (
    <Card className="flex items-center gap-4 p-6">
      <Icon className="w-10 h-10 text-indigo-600" />
      <div>
        <p className="text-3xl font-bold leading-none">{value}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{label}</p>
      </div>
    </Card>
  );

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <h1 className="text-3xl font-bold flex gap-2 items-center">
        <LayoutDashboard className="w-7 h-7 text-indigo-600" /> Dashboard
      </h1>

      {/* KPI row */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard icon={FolderOpen} label="Projects" value={stats.projects} />
        <StatCard icon={FileText} label="Documents" value={stats.documents} />
        <StatCard icon={Users2} label="Approvals" value={stats.approvals} />
      </div>

      {/* Analytics Tabs */}
      <Tabs defaultValue="projects" className="mt-6 space-y-4">
        <TabsList>
          <TabsTrigger value="projects">Projects</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>
        <TabsContent value="projects">
          <CardContent className="h-64 overflow-y-auto rounded-lg bg-gray-50 dark:bg-gray-900 p-4">
            <select
              className="mb-2 border rounded p-1"
              value={projectFilter ?? ""}
              onChange={(e) => setProjectFilter(e.target.value || null)}
            >
              <option value="">All projects</option>
              {Array.from(new Set(logs.map((l) => l.metadata?.project))).map(
                (id) =>
                  id && (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  )
              )}
            </select>
            <ul className="text-sm space-y-1">
              {logs
                .filter((l) => !projectFilter || l.metadata?.project === projectFilter)
                .map((l, i) => (
                  <li key={i}>{l.timestamp.slice(0, 10)} – {l.action}</li>
                ))}
            </ul>
          </CardContent>
        </TabsContent>
        <TabsContent value="activity">
          <CardContent className="h-64 flex items-center justify-center rounded-lg bg-gray-50 dark:bg-gray-900">
            <BarChart2 className="w-16 h-16 text-gray-400" />
            <span className="ml-4 text-gray-500 dark:text-gray-400">Activity chart placeholder…</span>
          </CardContent>
        </TabsContent>
      </Tabs>
    </div>
  );
}
