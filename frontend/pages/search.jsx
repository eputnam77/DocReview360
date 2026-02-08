import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Input, Button, } from "@/components";
import { API } from "@/lib/api";
export default function SearchPage() {
    const router = useRouter();
    const { q } = router.query;
    const [query, setQuery] = useState(q || "");
    const [results, setResults] = useState([]);
    useEffect(() => {
        if (!q)
            return;
        fetch(`${API}/search?q=${encodeURIComponent(q)}`)
            .then((r) => (r.ok ? r.json() : []))
            .then((data) => setResults(Array.isArray(data) ? data : []))
            .catch(() => setResults([]));
    }, [q]);
    function onSubmit(e) {
        e.preventDefault();
        if (query.trim()) {
            router.push(`/search?q=${encodeURIComponent(query.trim())}`);
        }
    }
    return (<div className="p-8 space-y-6">
      <form onSubmit={onSubmit} className="flex gap-2 max-w-md">
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search all content..."/>
        <Button type="submit">Search</Button>
      </form>
      <Table caption="Search results" className="min-w-full text-sm rounded-lg overflow-hidden bg-white">
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Project</TableHead>
            <TableHead>Preview</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((r) => (<TableRow key={r.id} className="border-t last:border-none">
              <TableCell className="font-mono text-xs">
                <Link href={`/projects/${r.project || ""}`}>{r.id}</Link>
              </TableCell>
              <TableCell>{r.project || ""}</TableCell>
              <TableCell>{r.content.slice(0, 40)}</TableCell>
            </TableRow>))}
          {results.length === 0 && (<TableRow>
              <TableCell colSpan={3} className="text-center py-4 text-gray-400">
                No results found.
              </TableCell>
            </TableRow>)}
        </TableBody>
      </Table>
    </div>);
}
