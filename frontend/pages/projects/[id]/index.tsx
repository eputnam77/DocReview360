import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [wordFile, setWordFile] = useState<File | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`/api/projects/${id}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setProject(data))
      .catch(() => setProject(null))
      .finally(() => setLoading(false));
    fetch(`/api/projects/${id}/workflow`)
      .then((r) => r.json())
      .then((wf: Workflow) => {
        setWorkflow(wf);
          return fetch(`/api/approvals?workflow=${wf.id}`);
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
        setLogs(data.filter((l) => l.metadata?.project === id)),
      )
      .catch(() => setLogs([]));
  }, [id]);

  const startSign = (aid: string) => {
    fetch(`/api/approvals/${aid}/sign`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        window.location.href = data.url;
      });
  };

  const handleWordUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!wordFile) return;
    const formData = new FormData();
    formData.append("file", wordFile);
    formData.append("project", String(id));
    const res = await fetch("/api/documents/import", {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      setWordFile(null);
      // simple feedback
      alert("Upload complete");
    } else {
      alert("Upload failed");
    }
  };

  if (loading) return <p className="p-4">Loading…</p>;
  if (!project) return <p className="p-4">Project not found.</p>;

  const editor = project.editor ?? "tiptap";
  const editDocUrl = `/editors/${editor}?projectId=${id}&returnTo=/projects/${id}`;

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

      {project.editor === "word" && (
        <div className="space-y-2">
          <Button asChild>
            <a href={`/documents/${project.id}/export?fmt=docx`}>
              Download DOCX
            </a>
          </Button>
          <form
            onSubmit={handleWordUpload}
            className="flex items-center gap-2"
            encType="multipart/form-data"
          >
            <Input
              type="file"
              accept=".docx"
              onChange={(e) => setWordFile(e.target.files?.[0] ?? null)}
            />
            <Button type="submit" disabled={!wordFile}>
              Upload DOCX
            </Button>
          </form>
        </div>
      )}

      <Button asChild>
        <Link href={editDocUrl}>Edit Document</Link>
      </Button>
    </div>
  );
}
