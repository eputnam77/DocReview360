"use client";
import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, } from "@/components/ui/table";
import { FixedSizeList as List } from "react-window";
const sample = [
    {
        id: "1",
        reviewer: "Alice",
        routing: "R1",
        pagePara: "1/1",
        comment: "Sample comment",
        change: "Update text",
        decision: "Accepted",
        disposition: "Fixed",
        phase: "Draft",
        tags: ["typo"],
    },
];
function useDebounce(value, delay) {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const id = setTimeout(() => setDebounced(value), delay);
        return () => clearTimeout(id);
    }, [value, delay]);
    return debounced;
}
export default function ReviewWorkspacePage() {
    const router = useRouter();
    const { reviewId } = router.query;
    const [comments, setComments] = useState(sample);
    const [selected, setSelected] = useState(null);
    const [phaseFilter, setPhaseFilter] = useState("");
    const [reviewerFilter, setReviewerFilter] = useState("");
    const [statusFilter, setStatusFilter] = useState("");
    const [tagFilter, setTagFilter] = useState("");
    const [view, setView] = useState("thread");
    const [search, setSearch] = useState("");
    const debouncedSearch = useDebounce(search, 300);
    const pageSize = 50;
    const [page, setPage] = useState(0);
    const updateDecision = (id, decision) => {
        setComments((prev) => prev.map((c) => (c.id === id ? { ...c, decision } : c)));
    };
    useEffect(() => {
        const handler = (e) => {
            if (!selected)
                return;
            const key = e.key.toLowerCase();
            if (key === "a")
                updateDecision(selected, "Accepted");
            if (key === "r")
                updateDecision(selected, "Rejected");
            if (key === "d")
                updateDecision(selected, "Deferred");
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [selected]);
    const filtered = useMemo(() => {
        return comments.filter((c) => {
            return ((!phaseFilter || c.phase === phaseFilter) &&
                (!reviewerFilter || c.reviewer === reviewerFilter) &&
                (!statusFilter || c.decision === statusFilter) &&
                (!tagFilter || c.tags.includes(tagFilter)) &&
                (!debouncedSearch ||
                    `${c.reviewer} ${c.comment}`
                        .toLowerCase()
                        .includes(debouncedSearch.toLowerCase())));
        });
    }, [comments, phaseFilter, reviewerFilter, statusFilter, tagFilter, debouncedSearch]);
    useEffect(() => {
        setPage(0);
    }, [phaseFilter, reviewerFilter, statusFilter, tagFilter, debouncedSearch]);
    const paged = useMemo(() => {
        const start = page * pageSize;
        return filtered.slice(start, start + pageSize);
    }, [filtered, page, pageSize]);
    const pageCount = Math.ceil(filtered.length / pageSize);
    const Row = ({ index, style }) => {
        const d = paged[index];
        return (<TableRow key={d.id} onClick={() => setSelected(d.id)} className={selected === d.id ? "bg-gray-100" : undefined} style={style}>
        <TableCell>{d.reviewer}</TableCell>
        <TableCell>{d.routing}</TableCell>
        <TableCell>{d.pagePara}</TableCell>
        <TableCell className="max-w-xs truncate">{d.comment}</TableCell>
        <TableCell className="max-w-xs truncate">{d.change}</TableCell>
        <TableCell>{d.decision}</TableCell>
        <TableCell>{d.disposition}</TableCell>
      </TableRow>);
    };
    const unique = {
        phases: Array.from(new Set(comments.map((c) => c.phase))),
        reviewers: Array.from(new Set(comments.map((c) => c.reviewer))),
        decisions: Array.from(new Set(comments.map((c) => c.decision))),
        tags: Array.from(new Set(comments.flatMap((c) => c.tags))),
    };
    const exportCSV = () => {
        const header = [
            "Reviewer",
            "Routing",
            "Page/Para",
            "Comment",
            "Change",
            "Decision",
            "Disposition",
        ];
        const rows = filtered.map((c) => [
            c.reviewer,
            c.routing,
            c.pagePara,
            c.comment,
            c.change,
            c.decision,
            c.disposition,
        ].join(","));
        const csv = [header.join(","), ...rows].join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "comments.csv";
        a.click();
        URL.revokeObjectURL(url);
    };
    const exportXLSX = () => {
        const header = "<tr><th>Reviewer</th><th>Routing</th><th>Page/Para</th><th>Comment</th><th>Change</th><th>Decision</th><th>Disposition</th></tr>";
        const rows = filtered
            .map((c) => `<tr><td>${c.reviewer}</td><td>${c.routing}</td><td>${c.pagePara}</td><td>${c.comment}</td><td>${c.change}</td><td>${c.decision}</td><td>${c.disposition}</td></tr>`)
            .join("");
        const html = `<table>${header}${rows}</table>`;
        const blob = new Blob([html], {
            type: "application/vnd.ms-excel",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "comments.xlsx";
        a.click();
        URL.revokeObjectURL(url);
    };
    const matrix = useMemo(() => {
        const result = {};
        comments.forEach((c) => {
            const disp = c.disposition || "";
            const dec = c.decision || "";
            result[disp] = result[disp] || {};
            result[disp][dec] = (result[disp][dec] || 0) + 1;
        });
        return result;
    }, [comments]);
    return (<div className="flex h-screen">
      <aside className="w-1/4 border-r p-4 space-y-4 overflow-auto">
        <h2 className="text-lg font-semibold">Filters</h2>
        <div>
          <label className="block text-sm">Phase</label>
          <select className="mt-1 w-full border p-1" value={phaseFilter} onChange={(e) => setPhaseFilter(e.target.value)}>
            <option value="">All</option>
            {unique.phases.map((p) => (<option key={p}>{p}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-sm">Reviewer</label>
          <select className="mt-1 w-full border p-1" value={reviewerFilter} onChange={(e) => setReviewerFilter(e.target.value)}>
            <option value="">All</option>
            {unique.reviewers.map((r) => (<option key={r}>{r}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-sm">Status</label>
          <select className="mt-1 w-full border p-1" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {unique.decisions.map((s) => (<option key={s}>{s}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-sm">Tags</label>
          <select className="mt-1 w-full border p-1" value={tagFilter} onChange={(e) => setTagFilter(e.target.value)}>
            <option value="">All</option>
            {unique.tags.map((t) => (<option key={t}>{t}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-sm">Search</label>
          <input className="mt-1 w-full border p-1" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search comments"/>
        </div>
        <div className="space-x-2 pt-2">
          <Button onClick={exportCSV}>Export CSV</Button>
          <Button onClick={exportXLSX} variant="outline">
            Export XLSX
          </Button>
        </div>
        <div className="pt-2">
          <Button variant="secondary" onClick={() => setView((v) => (v === "thread" ? "matrix" : "thread"))}>
            {view === "thread" ? "Show Dispo Matrix" : "Show Thread"}
          </Button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-4">
        {view === "thread" ? (<Card>
            <CardHeader>
              <CardTitle>Comments & Disposition</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table caption="Review comments">
                <TableHeader>
                  <TableRow>
                    <TableHead>Reviewer</TableHead>
                    <TableHead>Routing</TableHead>
                    <TableHead>Page/Para</TableHead>
                    <TableHead>Comment</TableHead>
                    <TableHead>Change</TableHead>
                    <TableHead>Decision</TableHead>
                    <TableHead>Disposition</TableHead>
                  </TableRow>
                </TableHeader>
                {paged.length > 0 ? (<List height={Math.min(400, paged.length * 48)} itemCount={paged.length} itemSize={48} width="100%" outerElementType={TableBody}>
                    {Row}
                  </List>) : (<TableBody>
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        No comments found
                      </TableCell>
                    </TableRow>
                  </TableBody>)}
              </Table>
              {pageCount > 1 && (<div className="flex justify-end items-center gap-2 mt-2 text-sm">
                  <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                    Previous
                  </Button>
                  <span>
                    Page {page + 1} of {pageCount}
                  </span>
                  <Button size="sm" variant="outline" disabled={page + 1 >= pageCount} onClick={() => setPage((p) => p + 1)}>
                    Next
                  </Button>
                </div>)}
            </CardContent>
          </Card>) : (<Card>
            <CardHeader>
              <CardTitle>Disposition Matrix</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table caption="Disposition counts">
                <TableHeader>
                  <TableRow>
                    <TableHead>Disposition</TableHead>
                    {unique.decisions.map((d) => (<TableHead key={d}>{d}</TableHead>))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(matrix).map(([disp, counts]) => (<TableRow key={disp}>
                      <TableCell>{disp}</TableCell>
                      {unique.decisions.map((d) => (<TableCell key={d}>{counts[d] || 0}</TableCell>))}
                    </TableRow>))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>)}
      </main>
      <aside className="w-1/4 border-l p-4 overflow-auto">
        <h2 className="text-lg font-semibold">Document Context</h2>
        <p className="text-sm text-gray-600">
          Preview the relevant document snippet here.
        </p>
      </aside>
    </div>);
}
