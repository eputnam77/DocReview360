import React, { useEffect, useState } from "react";
import {
  Card,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { FileText, RefreshCw, Plus } from "@/components/icons";

/**
 * ProjectTracker – switchable Table/Kanban view for projects.
 * Drop into your router as <ProjectTracker />.
 */
export default function ProjectTracker() {
  type Status = "New" | "Drafting" | "Review" | "Completed";
  type Project = {
    id: string;
    name: string;
    status: Status;
    owner: string;
    progress: number;
    due: string;
  };

  const [view, setView] = useState<"table" | "kanban">("table");
  const [projects, setProjects] = useState<Project[]>([]);

  // Fetch project data (replace with real API)
  useEffect(() => {
    fetch("/api/projects")
      .then((r) => r.json())
      .then(setProjects)
      .catch(() => {
        // Fallback mock data
        setProjects([
          {
            id: "PRJ-001",
            name: "AC 120-76F",
            status: "Review",
            owner: "Jane",
            progress: 60,
            due: "2025-07-31",
          },
          {
            id: "PRJ-002",
            name: "Style Guide v3",
            status: "Drafting",
            owner: "John",
            progress: 30,
            due: "2025-08-15",
          },
          {
            id: "PRJ-003",
            name: "Part 21 Rewrite",
            status: "New",
            owner: "Lisa",
            progress: 5,
            due: "2025-09-01",
          },
        ]);
      });
  }, []);

  /* ----------------------------- Table View ----------------------------- */
  const TableView = () => (
    <div className="overflow-x-auto rounded-lg border bg-white dark:bg-gray-950">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-900">
          <tr className="uppercase text-gray-600 dark:text-gray-400 font-medium tracking-wide text-xs">
            <th className="p-3 text-left">ID</th>
            <th className="p-3 text-left">Project</th>
            <th className="p-3 text-left">Owner</th>
            <th className="p-3 text-left">Status</th>
            <th className="p-3 text-left">Progress</th>
            <th className="p-3 text-left">Due</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => (
            <tr
              key={p.id}
              className="border-t last:border-none hover:bg-gray-50 dark:hover:bg-gray-900"
            >
              <td className="p-3 font-mono text-xs text-gray-500">{p.id}</td>
              <td className="p-3 font-medium">{p.name}</td>
              <td className="p-3">{p.owner}</td>
              <td className="p-3">
                <BadgeStatus status={p.status} />
              </td>
              <td className="p-3 w-48">
                <Progress value={p.progress} />
              </td>
              <td className="p-3">{p.due}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  /* ----------------------------- Kanban View ---------------------------- */
  const KanbanView = () => {
    const columns: Status[] = ["New", "Drafting", "Review", "Completed"];
    return (
      <div className="grid lg:grid-cols-4 gap-4">
        {columns.map((col) => (
          <div
            key={col}
            className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 flex flex-col gap-4"
          >
            <h3 className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <span>{col}</span>
              <span className="text-xs bg-gray-200 dark:bg-gray-800 rounded-full px-2">
                {projects.filter((p) => p.status === col).length}
              </span>
            </h3>
            {projects
              .filter((p) => p.status === col)
              .map((p) => (
                <Card
                  key={p.id}
                  className="p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                >
                  <CardTitle className="text-sm leading-tight line-clamp-2 mb-1">
                    {p.name}
                  </CardTitle>
                  <CardDescription className="flex justify-between items-center text-xs">
                    <span className="font-mono">{p.id}</span>
                    <span>{p.owner}</span>
                  </CardDescription>
                  <Progress value={p.progress} className="mt-2" />
                </Card>
              ))}
          </div>
        ))}
      </div>
    );
  };

  /* --------------------------------------------------------------------- */
  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-2">
          <FileText className="w-6 h-6 text-indigo-600" />
          <h1 className="text-2xl font-bold">Project Tracker</h1>
        </div>
        <div className="flex items-center gap-2">
          <Select value={view} onValueChange={(v) => setView(v as any)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="table">Table</SelectItem>
              <SelectItem value="kanban">Kanban</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={() => window.location.reload()}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button asChild className="gap-2">
            <a href="/projects/new">
              <Plus className="w-4 h-4" /> New Project
            </a>
          </Button>
        </div>
      </div>

      {/* Content */}
      {view === "table" ? <TableView /> : <KanbanView />}
    </div>
  );
}

/** Helper badge component */
function BadgeStatus({ status }: { status: "New" | "Drafting" | "Review" | "Completed" }) {
  const colors: Record<string, string> = {
    New: "bg-green-100 text-green-700",
    Drafting: "bg-yellow-100 text-yellow-800",
    Review: "bg-indigo-100 text-indigo-700",
    Completed: "bg-blue-100 text-blue-700",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>{status}</span>
  );
}
