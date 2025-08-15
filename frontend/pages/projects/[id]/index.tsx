import React, { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { useUserStore } from "@/state/user";

interface LogEntry {
  id: string;
  timestamp: string;
  action: string;
  user_id?: string;
  entity_id?: string;
  severity?: string;
  details?: Record<string, any>;
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filters, setFilters] = useState({
    start: "",
    end: "",
    user_id: "",
    entity_id: "",
    action: "",
    severity: "",
  });
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const username = useUserStore((s) => s.username);
  const isAdmin = useUserStore((s) => s.isAdmin);
  const isAuditor = useUserStore((s) => s.isAuditor);
  const allowed = isAdmin || isAuditor;

  useEffect(() => {
    if (!allowed) return;

    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params.append(k, v as string);
    });
    params.append("limit", String(PAGE_SIZE));
    params.append("offset", String(page * PAGE_SIZE));

    fetch(`${API}/audit?${params.toString()}`, {
      headers: { "X-User": username },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: LogEntry[]) => setLogs(data))
      .catch(() => setLogs([]));
  }, [allowed, username, filters, page]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
    setPage(0);
  };

  if (!allowed) {
    return (
      <div className="p-8 space-y-6">
        <h1 className="text-2xl font-bold">Audit Logs</h1>
        <p>You do not have permission to view audit logs.</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Audit Logs</h1>

      {/* Filters form */}
      <form className="flex flex-wrap gap-2">
        <Input
          type="date"
          name="start"
          value={filters.start}
          onChange={handleChange}
          className="w-40"
        />
        <Input
          type="date"
          name="end"
          value={filters.end}
          onChange={handleChange}
          className="w-40"
        />
        <Input
          placeholder="User"
          name="user_id"
          value={filters.user_id}
          onChange={handleChange}
          className="w-32"
        />
        <Input
          placeholder="Entity"
          name="entity_id"
          value={filters.entity_id}
          onChange={handleChange}
          className="w-32"
        />
        <Input
          placeholder="Action"
          name="action"
          value={filters.action}
          onChange={handleChange}
          className="w-32"
        />
        <Input
          placeholder="Severity"
          name="severity"
          value={filters.severity}
          onChange={handleChange}
          className="w-32"
        />
      </form>

      {/* Table */}
      <Table caption="Audit log entries">
        <TableHeader>
          <TableRow>
            <TableHead className="w-40">Timestamp</TableHead>
            <TableHead className="w-32">User</TableHead>
            <TableHead className="w-32">Entity</TableHead>
            <TableHead>Message</TableHead>
            <TableHead className="w-24">Severity</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.map((log, idx) => (
            <TableRow key={idx}>
              <TableCell className="font-mono whitespace-nowrap">
                {new Date(log.timestamp).toLocaleString()}
              </TableCell>
              <TableCell>
                {log.user_id || <span className="text-gray-400">—</span>}
              </TableCell>
              <TableCell>
                {log.entity_id || log.details?.project || (
                  <span className="text-gray-400">—</span>
                )}
              </TableCell>
              <TableCell>{log.details?.message || log.action}</TableCell>
              <TableCell>{log.severity || "info"}</TableCell>
            </TableRow>
          ))}
          {logs.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No audit logs recorded.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      <div className="flex justify-between">
        <Button
          variant="secondary"
          onClick={() => setPage((p) => Math.max(p - 1, 0))}
          disabled={page === 0}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          onClick={() => setPage((p) => p + 1)}
          disabled={logs.length < PAGE_SIZE}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
