import React, { useEffect, useMemo, useState } from "react";
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
import { useUserStore } from "@/state/user";
import { authenticatedFetch } from "@/lib/api";

// The Project type: extend as needed
interface Project {
  id: string;
  number: string | number;
  document_number?: string; // User-provided document number/reference
  type: string;
  title: string;
  status?: string;
  progress: number;
  updated?: string;
  user?: string;
  currentPhaseId?: string | null;
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
  const [viewMode, setViewMode] = useState<"assigned" | "all">("assigned");
  const username = useUserStore((s) => s.username);
  const isAdmin = useUserStore((s) => s.isAdmin);

  useEffect(() => {
    setViewMode(isAdmin ? "all" : "assigned");
  }, [isAdmin]);

  useEffect(() => {
    if (!username) {
      setProjects([]);
      return;
    }

    const endpoint = isAdmin
      ? "/projects"
      : `/projects?user=${encodeURIComponent(username)}`;

    authenticatedFetch(endpoint)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any) =>
        setProjects(
          Array.isArray(data)
            ? data.map((p: any) => ({
                ...p,
                currentPhaseId: p.current_phase_id ?? p.phase ?? null,
              }))
            : [],
        ),
      )
      .catch(() => setProjects([]));
  }, [isAdmin, username]);

  const isAssignedToUser = useMemo(
    () =>
      function isAssigned(project: Project) {
        if (!username) {
          return false;
        }

        const normalized = username.toLowerCase();
        const directMatches = [
          project.user,
          (project as any).owner,
          (project as any).assigned_to,
          (project as any).assignee,
        ];

        if (
          directMatches.some(
            (value) =>
              typeof value === "string" && value.toLowerCase() === normalized,
          )
        ) {
          return true;
        }

        const listMatches = (project as any).assignees;
        if (Array.isArray(listMatches)) {
          return listMatches.some(
            (value) =>
              typeof value === "string" && value.toLowerCase() === normalized,
          );
        }

        return false;
      },
    [username],
  );

  const assignedProjects = useMemo(
    () => projects.filter((project) => isAssignedToUser(project)),
    [isAssignedToUser, projects],
  );

  const visibleProjects = useMemo(() => {
    if (isAdmin && viewMode === "assigned") {
      return assignedProjects;
    }
    return projects;
  }, [assignedProjects, isAdmin, projects, viewMode]);

  const statAssigned = visibleProjects.length;
  const statInProgress = visibleProjects.filter(
    (p) => p.status?.toLowerCase() === "in progress",
  ).length;
  const statCompleted = visibleProjects.filter(
    (p) => p.status?.toLowerCase() === "complete",
  ).length;
  const statOverdue = visibleProjects.filter(
    (p) => p.status?.toLowerCase() === "overdue",
  ).length;

  const sorted = [...visibleProjects].sort((a, b) => {
    const av = (a as any)[sortKey] ?? "";
    const bv = (b as any)[sortKey] ?? "";
    if (typeof av === "number" && typeof bv === "number") return av - bv;
    return String(av).localeCompare(String(bv));
  });

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          {isAdmin && viewMode === "all"
            ? "All Projects"
            : "Projects Assigned to Me"}
        </h1>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          {isAdmin && (
            <div className="flex items-center gap-2">
              <Button
                variant={viewMode === "all" ? "default" : "outline"}
                onClick={() => setViewMode("all")}
              >
                All Projects
              </Button>
              <Button
                variant={viewMode === "assigned" ? "default" : "outline"}
                onClick={() => setViewMode("assigned")}
              >
                Assigned to Me
              </Button>
            </div>
          )}
          <Button asChild>
            <Link href="/projects/new">Create New Project</Link>
          </Button>
        </div>
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
      <Table caption="Projects" className="min-w-full text-sm rounded-lg overflow-hidden bg-white">
        <TableHeader>
          <TableRow>
            <TableHead
              onClick={() => setSortKey("id")}
              className="cursor-pointer"
            >
              Project ID
            </TableHead>
            <TableHead
              onClick={() => setSortKey("document_number")}
              className="cursor-pointer"
            >
              Document Number
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
          {sorted.map((p) => {
            const isMine = isAssignedToUser(p);
            return (
              <TableRow
                key={p.id}
                className={cn(
                  "border-t last:border-none transition-colors",
                  isMine
                    ? "bg-indigo-50/60 hover:bg-indigo-100"
                    : "hover:bg-gray-50",
                )}
              >
                <TableCell className="font-mono text-xs">
                  <Link
                    className="underline text-indigo-700"
                    href={`/projects/${p.id}`}
                  >
                    {p.id.slice(0, 8)}...
                  </Link>
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {p.document_number || p.number}
                </TableCell>
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
                              : "bg-gray-100 text-gray-700",
                    )}
                  >
                    {p.status || "Unknown"}
                  </span>
                </TableCell>
                <TableCell className="min-w-[100px] w-32">
                  <ProgressBar value={p.progress} />
                </TableCell>
                <TableCell>{p.updated?.slice(0, 10) ?? ""}</TableCell>
              </TableRow>
            );
          })}
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
