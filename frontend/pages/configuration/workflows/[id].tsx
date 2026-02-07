import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import {
  Card, CardHeader, CardTitle, CardContent,
} from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Edit3, Users2, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

export default function WorkflowDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [workflow, setWorkflow] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    if (!id) return;
    const wfId = String(id);
    // Retrieve workflow template details via local API route
    fetch(`/api/workflow-templates/${wfId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          const steps = Array.isArray(data.steps)
            ? data.steps
            : Array.isArray(data.approval_steps)
              ? data.approval_steps.map((s: any, idx: number) => ({
                  id: s.id ?? idx,
                  role: s.role ?? s.name ?? "",
                  user: s.user ?? "",
                  required: typeof s.required === "boolean" ? s.required : true,
                }))
              : Array.isArray(data.phases)
                ? data.phases.map((p: any, idx: number) => ({
                    id: idx,
                    role: typeof p === "string" ? p : String(p),
                    user: "",
                    required: true,
                  }))
                : [];
          const wfName = data.name ?? data.project ?? data.template ?? data.id;
          const wfDescription = data.description ?? "";
          setWorkflow({ ...data, name: wfName, description: wfDescription, steps });
          setLogs(Array.isArray(data.logs) ? data.logs : []);
        }
      })
      .catch(() => {});
  }, [id]);

  if (!workflow) return <p className="p-4">Loading…</p>;

  return (
    <div className="p-8 space-y-8">
      {/* Workflow Overview */}
      <Card>
        <CardHeader className="flex flex-row justify-between items-center">
          <div>
            <CardTitle className="text-2xl font-bold flex gap-2 items-center">
              Workflow: {workflow.name}
            </CardTitle>
            <p className="text-gray-500 text-sm mt-1">{workflow.description}</p>
          </div>
          <div className="flex gap-2">
            <Button asChild>
              <Link href={`/configuration/workflows/edit?id=${workflow.id}`}>
                <Edit3 className="w-5 h-5 mr-2" />
                Edit Workflow
              </Link>
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (!confirm("Delete this workflow template? This cannot be undone.")) return;
                const res = await fetch(`/api/workflow-templates/${workflow.id}`, {
                  method: "DELETE",
                });
                if (res.ok) {
                  router.push("/configuration/workflows");
                }
              }}
            >
              Delete
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-6 mb-4">
            <div className="flex items-center gap-1">
              <Users2 className="w-5 h-5 text-indigo-600" />
              <span className="text-xs text-gray-500">Used in</span>
              <span className="font-bold text-sm">{workflow.usage} projects</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-5 h-5 text-orange-600" />
              <span className="text-xs text-gray-500">Updated</span>
              <span className="font-bold text-sm">{workflow.updated}</span>
            </div>
          </div>
          <Table caption="Workflow details" className="mb-0">
            <TableHeader>
              <TableRow>
                <TableHead>Order</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Required</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workflow.steps.length > 0 ? (
                workflow.steps.map((s: any, idx: number) => (
                  <TableRow key={s.id ?? idx}>
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell>{s.role}</TableCell>
                    <TableCell>{s.user}</TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "px-2 py-1 rounded text-xs font-medium",
                          s.required ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-500"
                        )}
                      >
                        {s.required ? "Yes" : "No"}
                      </span>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-gray-500">
                    No steps defined.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Audit Trail */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Workflow History</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 text-sm">
            {logs.map((l, idx) => (
              <li key={idx}>{l.timestamp} – {l.action}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
