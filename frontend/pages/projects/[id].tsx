import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface LogEntry {
  timestamp: string;
  action: string;
  metadata?: Record<string, any>;
}

interface Project {
  id: string;
  name: string;
  number?: number;
  user?: string;
  created?: string;
  // Optionally: editor?: "tiptap" | "toast" | "codex" | "word";
}

interface Workflow {
  id: string;
  phase: string;
}

interface Approval {
  id: string;
  reviewer: string;
  state: string;
  documensoSigId?: string; // for Documenso integration
}

export default function ProjectDetails() {
  const router = useRouter();
  const { id } = router.query;
  const [project, setProject] = useState<Project | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);

  useEffect(() => {
    if (!id) return;
    fetch(`/projects/${id}`)
      .then((r) => r.json())
      .then(setProject)
      .catch(() => setProject(null));
    fetch(`/projects/${id}/workflow`)
      .then((r) => r.json())
      .then((wf: Workflow) => {
        setWorkflow(wf);
        return fetch(`/approvals?workflow=${wf.id}`);
      })
      .then((r) => (r ? r.json() : []))
      .then((data: Approval[]) => setApprovals(data))
      .catch(() => {
        setWorkflow(null);
        setApprovals([]);
      });
    fetch("/api/audit")
      .then((r) => r.json())
      .then((data: LogEntry[]) =>
        setLogs(data.filter((l) => l.metadata?.project === id))
      )
      .catch(() => setLogs([]));
  }, [id]);

  const startSign = (aid: string) => {
    fetch(`/approvals/${aid}/sign`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        window.location.href = data.url;
      });
  };

  if (!project) return <p className="p-4">Loading…</p>;

  // Default to TipTap editor for now
  const editDocUrl = `/editors/tiptap?projectId=${id}&returnTo=/projects/${id}`;

  return (
    <div className="p-8 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">
            Project {project.number}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p>
            <strong>Title:</strong> {project.name}
          </p>
          <p>
            <strong>Owner:</strong> {project.user ?? "–"}
          </p>
        </CardContent>
      </Card>

      <div>
        <h2 className="text-lg font-semibold">Audit History</h2>
        <ul className="list-disc pl-5">
          {logs.map((l, idx) => (
            <li key={idx}>
              {l.timestamp.slice(0, 10)} – {l.action}
            </li>
          ))}
        </ul>
      </div>

      {workflow && (
        <div>
          <h2 className="text-lg font-semibold mt-6">Approvals</h2>
          <ul className="space-y-1">
            {approvals.map((a) => (
              <li key={a.id} className="flex items-center gap-2">
                <span className="flex-1">
                  {a.reviewer} – {a.state}
                </span>
                {a.state !== "approved" && (
                  <>
                    <Button
                      size="sm"
                      onClick={() => startSign(a.id)}
                      variant="secondary"
                    >
                      Approve (API)
                    </Button>
                    {/* Documenso Sign/Approve Link */}
                    {a.documensoSigId && (
                      <Button
                        size="sm"
                        asChild
                        className="ml-1"
                        variant="outline"
                      >
                        <Link
                          href={`/documentso/${a.documensoSigId}?returnTo=/projects/${id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Sign in Documenso
                        </Link>
                      </Button>
                    )}
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <Button asChild>
        <Link href={editDocUrl}>Edit Document</Link>
      </Button>
    </div>
  );
}
