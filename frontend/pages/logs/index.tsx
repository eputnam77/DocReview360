import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { API, authenticatedFetch, getStoredAccessToken } from "@/lib/api";
import { useUserStore } from "@/state/user";
import SeverityBadge, { SeverityLegend } from "@/components/SeverityBadge";

interface LogEntry {
  id: string;
  timestamp: string;
  action: string;
  user_id?: string;
  entity_id?: string;
  entity_type?: string;
  severity?: string;
  details?: Record<string, any>;
}

function EntityLink({
  id,
  type,
  fallback,
}: {
  id?: string;
  type?: string;
  fallback?: string;
}) {
  if (!id || !type) {
    return fallback ? (
      <span className="text-gray-400">{fallback}</span>
    ) : (
      <span className="text-gray-400">—</span>
    );
  }
  const normalizedType = type.toLowerCase();
  const href =
    normalizedType === "project" || normalizedType === "projects"
      ? `/projects/${encodeURIComponent(id)}`
      : normalizedType === "approval" || normalizedType === "approvals"
        ? `/reviews/${encodeURIComponent(id)}`
        : null;
  if (!href) {
    return <span className="text-gray-700">{id}</span>;
  }
  return (
    <Link href={href} className="text-blue-600 hover:underline">
      {id}
    </Link>
  );
}


function buildLogsWebSocketUrl(token: string | null): string {
  const apiUrl = new URL(API, window.location.origin);
  apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  apiUrl.pathname = "/ws/logs";
  apiUrl.search = "";
  if (token) apiUrl.searchParams.set("token", token);
  return apiUrl.toString();
}


export default function LiveLogsPage() {
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
  const [hasMore, setHasMore] = useState(true);
  const PAGE_SIZE = 50;
  const loader = useRef<HTMLDivElement | null>(null);
  const username = useUserStore((s) => s.username);
  const isAdmin = useUserStore((s) => s.isAdmin);
  const isAuditor = useUserStore((s) => s.isAuditor);
  const allowed = isAdmin || isAuditor;

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params.append(k, v as string);
    });
    params.append("page", String(page));
    params.append("size", String(PAGE_SIZE));
    authenticatedFetch(`/api/audit?${params.toString()}`, {
      headers: { "X-User": username },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: LogEntry[]) => {
        if (cancelled) return;
        setLogs((prev) => (page === 0 ? data : [...prev, ...data]));
        setHasMore(data.length === PAGE_SIZE);
      })
      .catch(() => {
        if (!cancelled) setLogs([]);
      });
    return () => {
      cancelled = true;
    };
  }, [allowed, username, filters, page]);

  // Stream new log entries over a WebSocket for real-time updates
  useEffect(() => {
    if (!allowed) return;
    const token = getStoredAccessToken();
    const socket = new WebSocket(buildLogsWebSocketUrl(token));
    socket.onmessage = (event) => {
      try {
        const entry = JSON.parse(event.data) as LogEntry;
        setLogs((prev) => [entry, ...prev]);
      } catch {
        // ignore malformed messages
      }
    };
    return () => socket.close();
  }, [allowed]);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore) {
        setPage((p) => p + 1);
      }
    });
    const el = loader.current;
    if (el) observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
    setPage(0);
    setHasMore(true);
    setLogs([]);
  };

  if (!allowed) {
    return (
      <div className="p-8 space-y-6">
        <h1 className="text-2xl font-bold">Live Logs</h1>
        <p>You do not have permission to view audit logs.</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Live Logs</h1>
      <SeverityLegend />
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
      <Table>
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
                <EntityLink
                  id={log.entity_id}
                  type={log.entity_type}
                  fallback={log.details?.project}
                />
              </TableCell>
              <TableCell>{log.details?.message || log.action}</TableCell>
              <TableCell>
                <SeverityBadge severity={log.severity} />
              </TableCell>
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
      <div ref={loader} />
    </div>
  );
}
