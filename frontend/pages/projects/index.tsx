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

interface Project {
  id: string;
  name: string;
  number?: number;
  user?: string;
  created?: string;
}

// Example data used when the API returns nothing.
const DEMO_PROJECTS: Project[] = [
  {
    id: "AC-101",
    name: "Policy Update",
    number: 101,
    user: "Jane Doe",
    created: "2025-07-04",
  },
  {
    id: "AC-102",
    name: "Compliance Review",
    number: 102,
    user: "Jane Doe",
    created: "2025-07-02",
  },
  {
    id: "AC-103",
    name: "Draft SOP",
    number: 103,
    user: "Jane Doe",
    created: "2025-07-01",
  },
  {
    id: "AC-104",
    name: "Incident Report",
    number: 104,
    user: "Jane Doe",
    created: "2025-07-03",
  },
];

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [sortKey, setSortKey] = useState<keyof Project | "number">("number");

  useEffect(() => {
    fetch("/api/projects") // <-- Use /api/projects for Next.js API, or your real endpoint
      .then((r) => r.json())
      .then((data: Project[]) => {
        setProjects(data.length > 0 ? data : DEMO_PROJECTS);
      })
      .catch(() => setProjects(DEMO_PROJECTS));
  }, []);

  const sorted = [...projects].sort((a, b) => {
    const av = (a as any)[sortKey] ?? "";
    const bv = (b as any)[sortKey] ?? "";
    if (typeof av === "number" && typeof bv === "number") return av - bv;
    return String(av).localeCompare(String(bv));
  });

  return (
    <div className="p-8 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Button asChild>
          <Link href="/projects/new">Create New Project</Link>
        </Button>
      </div>
      <Table className="min-w-full text-sm">
        <TableHeader>
          <TableRow>
            <TableHead onClick={() => setSortKey("number")}>
              Document #
            </TableHead>
            <TableHead onClick={() => setSortKey("name")}>Title</TableHead>
            <TableHead onClick={() => setSortKey("user")}>
              Assigned To
            </TableHead>
            <TableHead>Status</TableHead>
            <TableHead onClick={() => setSortKey("created")}>Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((p) => (
            <TableRow key={p.id} className="border-t last:border-none">
              <TableCell className="font-mono text-xs">
                <Link href={`/projects/${p.id}`}>{p.number ?? "-"}</Link>
              </TableCell>
              <TableCell>{p.name}</TableCell>
              <TableCell>{p.user ?? ""}</TableCell>
              <TableCell>{"N/A"}</TableCell>
              <TableCell>{p.created?.slice(0, 10) ?? ""}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
