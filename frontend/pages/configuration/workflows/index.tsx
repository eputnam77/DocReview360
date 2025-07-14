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

interface Workflow {
  id: string;
  name: string;
  usage: number;
  updated: string;
}

const DEMO_WORKFLOWS: Workflow[] = [
  { id: "ac-std", name: "Advisory Circular Standard Review", usage: 12, updated: "2025-07-06" },
  { id: "hr-onboarding", name: "Employee Onboarding", usage: 7, updated: "2025-06-20" },
];

export default function WorkflowList() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);

  useEffect(() => {
    fetch("/api/workflows")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Workflow[]) => setWorkflows(data.length ? data : DEMO_WORKFLOWS))
      .catch(() => setWorkflows(DEMO_WORKFLOWS));
  }, []);

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Workflows</h1>
        <Button asChild>
          <Link href="/configuration/workflows/new">Create Workflow</Link>
        </Button>
      </div>
      <Table className="min-w-full text-sm">
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Usage</TableHead>
            <TableHead>Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {workflows.map((w) => (
            <TableRow key={w.id} className="border-t last:border-none hover:bg-gray-50">
              <TableCell className="font-mono text-xs">
                <Link href={`/configuration/workflows/${w.id}`} className="underline text-indigo-700">
                  {w.id}
                </Link>
              </TableCell>
              <TableCell>{w.name}</TableCell>
              <TableCell>{w.usage}</TableCell>
              <TableCell>{w.updated}</TableCell>
            </TableRow>
          ))}
          {workflows.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No workflows found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
