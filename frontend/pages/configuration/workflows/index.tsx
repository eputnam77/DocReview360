import { Button } from "@/components/ui/button";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import Link from "next/link";
import { useEffect, useState } from "react";
import { API, authenticatedFetch } from "@/lib/api";

interface Workflow {
  id: string;
  name?: string;
  description?: string;
  usage?: number;
  updated?: string;
}

const normalizeWorkflows = (items: unknown): Workflow[] => {
  if (!Array.isArray(items)) return [];
  const normalized: Workflow[] = [];

  for (const item of items) {
    if (!item || typeof item !== "object") continue;

    const anyItem = item as {
      id?: unknown;
      name?: unknown;
      project?: unknown;
      template?: unknown;
      description?: unknown;
      usage?: unknown;
      updated?: unknown;
    };
    const id = typeof anyItem.id === "string" ? anyItem.id : String(anyItem.id ?? "");
    if (!id) continue;

    const name =
      typeof anyItem.name === "string"
        ? anyItem.name
        : typeof anyItem.project === "string"
        ? anyItem.project
        : typeof anyItem.template === "string"
        ? anyItem.template
        : "";
    const description = typeof anyItem.description === "string" ? anyItem.description : "";
    const usage = typeof anyItem.usage === "number" ? anyItem.usage : null;
    const updated = typeof anyItem.updated === "string" ? anyItem.updated : "";

    normalized.push({
      id,
      ...(name ? { name } : {}),
      ...(description ? { description } : {}),
      ...(usage !== null ? { usage } : {}),
      ...(updated ? { updated } : {}),
    });
  }

  return normalized;
};

export default function WorkflowList() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);

  useEffect(() => {
    // Use local API route to proxy to backend
    authenticatedFetch(`${API}/workflow-templates`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => setWorkflows(normalizeWorkflows(data)))
      .catch(() => setWorkflows([]));
  }, []);

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Workflows</h1>
        <Button asChild>
          <Link href="/configuration/workflows/new">Create Workflow</Link>
        </Button>
      </div>
      <Table caption="Workflows" className="min-w-full text-sm">
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Description</TableHead>
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
              <TableCell>{w.description}</TableCell>
              <TableCell>{w.usage}</TableCell>
              <TableCell>{w.updated}</TableCell>
            </TableRow>
          ))}
          {workflows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No workflows found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
