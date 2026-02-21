import React, { useEffect, useRef, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { API } from "@/lib/api";
import { useUserStore } from "@/state/user";
import SeverityBadge, { SeverityLegend } from "@/components/SeverityBadge";
export default function AuditLogsPage() {
    const [logs, setLogs] = useState([]);
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
    const loader = useRef(null);
    const username = useUserStore((s) => s.username);
    const isAdmin = useUserStore((s) => s.isAdmin);
    const isAuditor = useUserStore((s) => s.isAuditor);
    const allowed = isAdmin || isAuditor;
    useEffect(() => {
        if (!allowed)
            return;
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([k, v]) => {
            if (v)
                params.append(k, v);
        });
        params.append("page", String(page));
        params.append("size", String(PAGE_SIZE));
        fetch(`${API}/audit?${params.toString()}`, {
            headers: { "X-User": username },
        })
            .then((r) => (r.ok ? r.json() : []))
            .then((data) => {
            setLogs((prev) => (page === 0 ? data : [...prev, ...data]));
            setHasMore(data.length === PAGE_SIZE);
        })
            .catch(() => setLogs([]));
    }, [allowed, username, filters, page]);
    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && hasMore) {
                setPage((p) => p + 1);
            }
        });
        const el = loader.current;
        if (el)
            observer.observe(el);
        return () => observer.disconnect();
    }, [hasMore]);
    const handleChange = (e) => {
        const { name, value } = e.target;
        setFilters((f) => ({ ...f, [name]: value }));
        setPage(0);
        setHasMore(true);
        setLogs([]);
    };
    if (!allowed) {
        return (<div className="p-8 space-y-6">
        <h1 className="text-2xl font-bold">Audit Logs</h1>
        <p>You do not have permission to view audit logs.</p>
      </div>);
    }
    return (<div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Audit Logs</h1>
      <SeverityLegend />

      {/* Filter Form */}
      <form className="flex flex-wrap gap-2" onSubmit={(e) => e.preventDefault()}>
        <Input type="date" name="start" value={filters.start} onChange={handleChange} className="w-40"/>
        <Input type="date" name="end" value={filters.end} onChange={handleChange} className="w-40"/>
        <Input placeholder="User" name="user_id" value={filters.user_id} onChange={handleChange} className="w-32"/>
        <Input placeholder="Entity" name="entity_id" value={filters.entity_id} onChange={handleChange} className="w-32"/>
        <Input placeholder="Action" name="action" value={filters.action} onChange={handleChange} className="w-32"/>
        <Input placeholder="Severity" name="severity" value={filters.severity} onChange={handleChange} className="w-32"/>
      </form>

      {/* Table with caption */}
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
          {logs.map((log, idx) => (<TableRow key={idx}>
              <TableCell className="font-mono whitespace-nowrap">
                {new Date(log.timestamp).toLocaleString()}
              </TableCell>
              <TableCell>
                {log.user_id || <span className="text-gray-400">—</span>}
              </TableCell>
              <TableCell>
                {log.entity_id || log.details?.project || (<span className="text-gray-400">—</span>)}
              </TableCell>
              <TableCell>{log.details?.message || log.action}</TableCell>
              <TableCell>
                <SeverityBadge severity={log.severity}/>
              </TableCell>
            </TableRow>))}
          {logs.length === 0 && (<TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No audit logs recorded.
              </TableCell>
            </TableRow>)}
        </TableBody>
      </Table>

      <div ref={loader}/>
    </div>);
}
