import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, } from "@/components/ui/table";
import Link from "next/link";
import { useEffect, useState } from "react";
const normalizeWorkflows = (items) => {
    if (!Array.isArray(items))
        return [];
    return items
        .map((item) => {
        if (item && typeof item === "object") {
            const anyItem = item;
            const id = typeof anyItem.id === "string" ? anyItem.id : String(anyItem.id ?? "");
            if (!id)
                return null;
            const name = typeof anyItem.name === "string"
                ? anyItem.name
                : typeof anyItem.project === "string"
                    ? anyItem.project
                    : typeof anyItem.template === "string"
                        ? anyItem.template
                        : undefined;
            const description = typeof anyItem.description === "string" ? anyItem.description : undefined;
            const usage = typeof anyItem.usage === "number" ? anyItem.usage : undefined;
            const updated = typeof anyItem.updated === "string" ? anyItem.updated : undefined;
            return { id, name, description, usage, updated };
        }
        return null;
    })
        .filter((v) => Boolean(v));
};
export default function WorkflowList() {
    const [workflows, setWorkflows] = useState([]);
    useEffect(() => {
        // Use local API route to proxy to backend
        fetch("/api/workflow-templates")
            .then((r) => (r.ok ? r.json() : []))
            .then((data) => setWorkflows(normalizeWorkflows(data)))
            .catch(() => setWorkflows([]));
    }, []);
    return (<div className="p-8 space-y-8">
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
          {workflows.map((w) => (<TableRow key={w.id} className="border-t last:border-none hover:bg-gray-50">
              <TableCell className="font-mono text-xs">
                <Link href={`/configuration/workflows/${w.id}`} className="underline text-indigo-700">
                  {w.id}
                </Link>
              </TableCell>
              <TableCell>{w.name}</TableCell>
              <TableCell>{w.description}</TableCell>
              <TableCell>{w.usage}</TableCell>
              <TableCell>{w.updated}</TableCell>
            </TableRow>))}
          {workflows.length === 0 && (<TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No workflows found.
              </TableCell>
            </TableRow>)}
        </TableBody>
      </Table>
    </div>);
}
