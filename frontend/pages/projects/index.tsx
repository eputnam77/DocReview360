import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users2, CheckCircle2, Clock, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { DEMO_PROJECTS } from "@/data";
import { useUserStore } from "@/state/user";

// The Project type: extend as needed
interface Project {
  id: string;
  number: string | number;
  type: string;
  title: string;
  status: string;
  progress: number;
  updated?: string;
  user?: string;
}

// --- Simple stat cards (copied style from dashboard) ---
function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <Icon className={`w-8 h-8 ${color || "text-indigo-600"}`} />
        <div>
          <p className="text-xl font-bold leading-none">{value}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {label}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value || 0));
  const status =
    pct === 100
      ? "bg-green-500"
      : pct >= 70
      ? "bg-blue-500"
      : pct > 0
      ? "bg-yellow-400"
      : "bg-gray-300";
  return (
    <div className="w-full bg-gray-200 rounded-full h-3">
      <div
        className={cn(
          "h-3 rounded-full transition-all duration-200",
          status
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [sortKey, setSortKey] = useState<keyof Project>("number");
  const username = useUserStore((s) => s.username);
  const API = process.env.NEXT_PUBLIC_API_BASE ?? "";

  useEffect(() => {
    const headers: Record<string, string> = {};
    if (username) {
      headers["X-User"] = username;
    }
    fetch(`${API}/projects`, { headers })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Project[]) =>
        setProjects(data.length > 0 ? data : DEMO_PROJECTS)
      )
      .catch(() => setProjects(DEMO_PROJECTS));
  }, [username]);

  // Calculate simple stats for this user
  const statAssigned = projects.length;
  const statInProgress = projects.filter(
    (p) => p.status.toLowerCase() === "in progress"
  ).length;
  const statCompleted = projects.filter(
    (p) => p.status.toLowerCase() === "complete"
  ).length;
  const statOverdue = projects.filter(
    (p) => p.status.toLowerCase() === "overdue"
  ).length;

  const sorted = [...projects].sort((a, b) => {
    const av = (a as any)[sortKey] ?? "";
    const bv = (b as any)[sortKey] ?? "";
    if (typeof av === "number" && typeof bv === "number") return av - bv;
    return String(av).localeCompare(String(bv));
  });

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          Projects Assigned to Me
        </h1>
        <Button asChild>
          <Link href="/projects/new">Create New Project</Link>
        </Button>
      </div>

      {/* KPI Stat Row */}
      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-4 max-w-4xl">
        <StatCard
          icon={Users2}
          label="Assigned"
          value={statAssigned}
          color="text-indigo-600"
        />
        <StatCard
          icon={Clock}
          label="In Progress"
          value={statInProgress}
          color="text-orange-600"
        />
        <StatCard
          icon={CheckCircle2}
          label="Completed"
          value={statCompleted}
          color="text-emerald-600"
        />
        <StatCard
          icon={BarChart2}
          label="Overdue"
          value={statOverdue}
          color="text-red-600"
        />
      </div>

      {/* Project Table */}
      <Table className="min-w-full text-sm rounded-lg overflow-hidden bg-white">
        <TableHeader>
          <TableRow>
            <TableHead
              onClick={() => setSortKey("id")}
              className="cursor-pointer"
            >
              Document Id
            </TableHead>
            <TableHead
              onClick={() => setSortKey("number")}
              className="cursor-pointer"
            >
              Document #
            </TableHead>
            <TableHead
              onClick={() => setSortKey("type")}
              className="cursor-pointer"
            >
              Document Type
            </TableHead>
            <TableHead
              onClick={() => setSortKey("title")}
              className="cursor-pointer"
            >
              Document Title
            </TableHead>
            <TableHead
              onClick={() => setSortKey("status")}
              className="cursor-pointer"
            >
              Status
            </TableHead>
            <TableHead>Progress</TableHead>
            <TableHead
              onClick={() => setSortKey("updated")}
              className="cursor-pointer"
            >
              Updated
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((p) => (
            <TableRow
              key={p.id}
              className="border-t last:border-none hover:bg-gray-50"
            >
              <TableCell className="font-mono text-xs">
                <Link
                  className="underline text-indigo-700"
                  href={`/projects/${p.id}`}
                >
                  {p.id}
                </Link>
              </TableCell>
              <TableCell>{p.number}</TableCell>
              <TableCell>{p.type}</TableCell>
              <TableCell>{p.title}</TableCell>
              <TableCell>
                <span
                  className={cn(
                    "px-2 py-1 rounded text-xs font-medium",
                    p.status === "Complete"
                      ? "bg-green-100 text-green-800"
                      : p.status === "In Progress"
                      ? "bg-blue-100 text-blue-800"
                      : p.status === "Draft"
                      ? "bg-yellow-100 text-yellow-800"
                      : p.status === "Overdue"
                      ? "bg-red-100 text-red-800"
                      : "bg-gray-100 text-gray-700"
                  )}
                >
                  {p.status}
                </span>
              </TableCell>
              <TableCell className="min-w-[100px] w-32">
                <ProgressBar value={p.progress} />
              </TableCell>
              <TableCell>{p.updated?.slice(0, 10) ?? ""}</TableCell>
            </TableRow>
          ))}
          {sorted.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-gray-400 py-6">
                No projects found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
