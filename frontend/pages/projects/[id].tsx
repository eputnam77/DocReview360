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
}

export default function ProjectDetails() {
  const router = useRouter();
  const { id } = router.query;
  const [project, setProject] = useState<Project | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    if (!id) return;
    fetch(`/projects/${id}`)
      .then((r) => r.json())
      .then(setProject)
      .catch(() => setProject(null));
    fetch("/api/audit")
      .then((r) => r.json())
      .then((data: LogEntry[]) =>
        setLogs(data.filter((l) => l.metadata?.project === id))
      )
      .catch(() => setLogs([]));
  }, [id]);

  if (!project) return <p className="p-4">Loading…</p>;

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

      <Button>
        <Link href={`/doceditor?returnTo=/projects/${id}`}>Edit Document</Link>
      </Button>
    </div>
  );
}
