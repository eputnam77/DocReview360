import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import {
  Card, CardHeader, CardTitle, CardContent,
} from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Edit3, Users2, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { API } from "@/lib/api";

// Fallback for system workflow if API is unavailable
const DEFAULT_SYSTEM_WORKFLOW = {
  id: "branch-coordination",
  name: "branch-coordination",
  description:
    "Standard workflow with SME, Front Line Manager, Product Policy Manager, Technical Writer, Senior Technical Writer, and Technical Writing Manager steps",
  steps: [
    { id: "1", role: "Subject Matter Expert", user: "", required: true },
    { id: "2", role: "Front Line Manager", user: "", required: true },
    { id: "3", role: "Product Policy Manager", user: "", required: true },
    { id: "4", role: "Technical Writer", user: "", required: true },
    { id: "5", role: "Senior Technical Writer", user: "", required: true },
    { id: "6", role: "Technical Writing Manager", user: "", required: true },
  ],
  usage: 0,
  created: new Date().toISOString().split("T")[0],
  updated: new Date().toISOString().split("T")[0],
};

export default function WorkflowDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [workflow, setWorkflow] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    if (!id) return;
    const wfId = String(id);
    fetch(`${API}/workflows/${wfId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          setWorkflow(data);
          setLogs(data.logs ?? []);
        } else if (wfId === "branch-coordination") {
          setWorkflow(DEFAULT_SYSTEM_WORKFLOW);
          setLogs([
            { timestamp: DEFAULT_SYSTEM_WORKFLOW.created, action: "Workflow created" },
          ]);
        }
      })
      .catch(() => {
        if (wfId === "branch-coordination") {
          setWorkflow(DEFAULT_SYSTEM_WORKFLOW);
          setLogs([
            { timestamp: DEFAULT_SYSTEM_WORKFLOW.created, action: "Workflow created" },
          ]);
        }
      });
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
          <Button asChild>
            <a href={`/configuration/workflows/edit?id=${workflow.id}`}>
              <Edit3 className="w-5 h-5 mr-2" />
              Edit Workflow
            </a>
          </Button>
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
          <Table className="mb-0">
            <TableHeader>
              <TableRow>
                <TableHead>Order</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Required</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workflow.steps.map((s: any, idx: number) => (
                <TableRow key={s.id}>
                  <TableCell>{idx + 1}</TableCell>
                  <TableCell>{s.role}</TableCell>
                  <TableCell>{s.user}</TableCell>
                  <TableCell>
                    <span className={cn(
                      "px-2 py-1 rounded text-xs font-medium",
                      s.required ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-500"
                    )}>{s.required ? "Yes" : "No"}</span>
                  </TableCell>
                </TableRow>
              ))}
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
