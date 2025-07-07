import React, { useEffect, useState } from "react";
import {
  Button,
} from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import {
  LayoutDashboard,
  FolderOpen,
  Workflow,
  CirclePlay,
  Plus,
} from "lucide-react";

/**
 * Fancy landing page for DocuFlow
 * -------------------------------------------------
 * - Left sidebar with primary navigation (Projects, Status, Dashboard)
 * - Center content shows a grid/list of projects with quick‑action buttons
 * - Uses shadcn/ui + Tailwind CSS for styling
 */
export default function LandingPage() {
  type Project = {
    id: string;
    name: string;
    docs: number;
    pending_approvals: number;
  };

  const [projects, setProjects] = useState<Project[]>([]);

  // Fetch projects when component mounts
  useEffect(() => {
    fetch("/reports/dashboard")
      .then((r) => r.json())
      .then(setProjects)
      .catch(() => {
        /* fallback to mock data */
        setProjects([
          {
            id: "PRJ‑001",
            name: "FAA Advisory Circular 120‑76F",
            docs: 14,
            pending_approvals: 2,
          },
          {
            id: "PRJ‑002",
            name: "AIR‑646 Style Guide v3",
            docs: 7,
            pending_approvals: 0,
          },
        ]);
      });
  }, []);

  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-950">
      {/* ─────────── Sidebar ─────────── */}
      <aside className="hidden md:flex md:w-64 lg:w-72 flex-col gap-6 border-r bg-gray-900 text-gray-100 p-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Workflow className="w-6 h-6 text-indigo-400" /> DocuFlow
        </h1>

        <nav className="flex-1">
          <ul className="space-y-1 text-sm">
            <NavItem icon={FolderOpen} label="Projects" href="/projects" />
            <NavItem icon={CirclePlay} label="Status" href="/status" />
            <NavItem icon={LayoutDashboard} label="Dashboard" href="/dashboard" />
          </ul>
        </nav>

        <Button asChild size="sm" variant="secondary" className="w-full mt-auto">
          <a href="/new-project" className="flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Project
          </a>
        </Button>
      </aside>

      {/* ─────────── Main content ─────────── */}
      <main className="flex-1 p-8 overflow-y-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Projects</h2>
            <p className="text-gray-500 dark:text-gray-400">
              Quickly create, open, or manage your document flows.
            </p>
          </div>

          <Button asChild className="gap-2">
            <a href="/new-flow">
              <Plus className="w-4 h-4" /> Create New Flow
            </a>
          </Button>
        </div>

        {/* Project list */}
        {projects.length === 0 ? (
          <div className="text-center text-gray-500 dark:text-gray-400">
            No projects yet. Start by creating one.
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {projects.map((p: Project) => (
              <Card
                key={p.id}
                className="group hover:shadow-lg transition-shadow duration-200"
              >
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-start justify-between gap-2">
                    <span className="line-clamp-2 leading-tight">
                      {p.name}
                    </span>
                    <span className="text-xs font-mono text-gray-400 dark:text-gray-500">
                      {p.id}
                    </span>
                  </CardTitle>
                </CardHeader>

                <CardContent className="flex flex-col gap-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Documents</span>
                    <span className="font-medium">{p.docs}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500 dark:text-gray-400">
                      Pending approvals
                    </span>
                    <span className="font-medium">
                      {p.pending_approvals}
                    </span>
                  </div>

                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="w-full mt-2 group-hover:bg-indigo-50 dark:group-hover:bg-indigo-950"
                  >
                    <a href={`/projects/${p.id}`}>Open Project</a>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

/** ————————————————————————————————
 * Utility component for sidebar navigation items
 */
function NavItem({
  icon: Icon,
  label,
  href,
}: {
  icon: typeof FolderOpen;
  label: string;
  href: string;
}) {
  return (
    <li>
      <a
        href={href}
        className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-gray-800 transition-colors"
      >
        <Icon className="w-4 h-4 text-indigo-400" /> {label}
      </a>
    </li>
  );
}
