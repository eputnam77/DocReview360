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
  const [stats, setStats] = useState({ projects: 0, activeDocs: 0, users: 0 });

  useEffect(() => {
    fetch("/dashboard/widgets")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => setStats({ projects: 12, activeDocs: 43, users: 7 }));
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
        <StatCard icon={FileText} label="Active Docs" value={stats.activeDocs} />
        <StatCard icon={Users2} label="Users" value={stats.users} />
      </div>

      {/* Analytics Tabs */}
      <Tabs defaultValue="projects" className="mt-6">
        <TabsList>
          <TabsTrigger value="projects">Projects</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>
        <TabsContent value="projects">
          <CardContent className="h-64 flex items-center justify-center rounded-lg bg-gray-50 dark:bg-gray-900">
            <BarChart2 className="w-16 h-16 text-gray-400" />
            <span className="ml-4 text-gray-500 dark:text-gray-400">Projects chart coming soon…</span>
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
