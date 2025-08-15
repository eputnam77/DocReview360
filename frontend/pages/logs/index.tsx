import React, { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { API } from "@/lib/api";

interface LogEntry {
  timestamp: string;
  action: string;
  user?: string;
  metadata?: Record<string, any>;
}


export default function LiveLogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    fetch(`${API}/audit`)
      .then((r) => (r.ok ? r.json() : []))
        .then((data: LogEntry[]) =>
          setLogs(
            data.length
              ? data.sort(
                  (a, b) =>
                    new Date(b.timestamp).getTime() -
                    new Date(a.timestamp).getTime(),
                )
              : []
          )
        )
        .catch(() => setLogs([]));

    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${wsProtocol}://${window.location.host}/ws/logs`
    );
    ws.onmessage = (ev) => {
      const entry = JSON.parse(ev.data) as LogEntry;
      setLogs((prev) => [entry, ...prev]);
    };
    return () => ws.close();
  }, []);

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Live Logs</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-40">Timestamp</TableHead>
            <TableHead className="w-32">User</TableHead>
            <TableHead className="w-32">Project</TableHead>
            <TableHead>Message</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.map((log, idx) => (
            <TableRow key={idx}>
              <TableCell className="font-mono whitespace-nowrap">
                {new Date(log.timestamp).toLocaleString()}
              </TableCell>
              <TableCell>
                {log.user || log.metadata?.user || (
                  <span className="text-gray-400">—</span>
                )}
              </TableCell>
              <TableCell>
                {log.metadata?.project || <span className="text-gray-400">—</span>}
              </TableCell>
              <TableCell>{log.metadata?.message || log.action}</TableCell>
            </TableRow>
          ))}
          {logs.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No audit logs recorded.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
