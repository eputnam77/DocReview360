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
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Extended Project interface with all needed fields
interface Project {
  id: string;                  // System-generated, e.g., UUID or short id
  number: string | number;     // Document number, e.g., AC-123
  type: string;                // Document type (Order, AC, SOP, etc.)
  title: string;               // Document title
  status: string;              // Status string (e.g., In Progress, Complete)
  progress: number;            // 0-100 (percent complete)
  updated?: string;            // Last updated date
}

// Example/demo data
const DEMO_PROJECTS: Project[] = [
  {
    id: "123e-ac-101",
    number: "AC-101",
    type: "Advisory Circular",
    title: "Policy Update",
    status: "In Progress",
    progress: 40,
    updated: "2025-07-04",
  },
  {
    id: "123e-ac-102",
    number: "AC-102",
    type: "Order",
    title: "Compliance Review",
    status: "Complete",
    progress: 100,
    updated: "2025-07-02",
  },
  {
    id: "123e-ac-103",
    number: "AC-103",
    type: "SOP",
    title: "Draft SOP",
    status: "Draft",
    progress: 10,
    updated: "2025-07-01",
  },
  {
    id: "123e-ac-104",
    number: "AC-104",
    type: "Incident Report",
    title: "Incident Report",
    status: "Review",
    progress: 70,
    updated: "2025-07-03",
  },
];

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

  useEffect(() => {
    fetch("/api/projects")
      .then((r) => r.json())
      .then((data: Project[]) => setProjects(data.length > 0 ? data : DEMO_PROJECTS))
      .catch(() => setProjects(DEMO_PROJECTS));
  }, []);

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
        <h1 className="text-2xl font-bold flex items-center gap-2">Projects</h1>
        <Button asChild>
          <Link href="/projects/new">Create New Project</Link>
        </Button>
      </div>

      {/* Project Table */}
      <Table className="min-w-full text-sm rounded-lg overflow-hidden bg-white">
        <TableHeader>
          <TableRow>
            <TableHead onClick={() => setSortKey("id")} className="cursor-pointer">Document Id</TableHead>
            <TableHead onClick={() => setSortKey("number")} className="cursor-pointer">Document #</TableHead>
            <TableHead onClick={() => setSortKey("type")} className="cursor-pointer">Document Type</TableHead>
            <TableHead onClick={() => setSortKey("title")} className="cursor-pointer">Document Title</TableHead>
            <TableHead onClick={() => setSortKey("status")} className="cursor-pointer">Status</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead onClick={() => setSortKey("updated")} className="cursor-pointer">Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((p) => (
            <TableRow key={p.id} className="border-t last:border-none hover:bg-gray-50">
              <TableCell className="font-mono text-xs">
                <Link className="underline text-indigo-700" href={`/projects/${p.id}`}>{p.id}</Link>
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
