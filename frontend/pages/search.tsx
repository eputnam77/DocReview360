import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Input,
  Button,
} from "@/components";
import { authenticatedFetch } from "@/lib/api";
import { useTranslation } from "@/lib/useTranslation";


interface Result {
  id: string;
  project?: string;
  content: string;
}

export default function SearchPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { q } = router.query as { q?: string };
  const [query, setQuery] = useState(q || "");
  const [results, setResults] = useState<Result[]>([]);

  useEffect(() => {
    if (!q) return;
      authenticatedFetch(`/search?q=${encodeURIComponent(q)}`)
        .then((r) => (r.ok ? r.json() : []))
        .then((data) => setResults(Array.isArray(data) ? data : []))
        .catch(() => setResults([]));
  }, [q]);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <div className="p-8 space-y-6">
      <form onSubmit={onSubmit} className="flex gap-2 max-w-md">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("search.placeholder", "Search all content...")}
        />
        <Button type="submit">{t("search.button", "Search")}</Button>
      </form>
      <Table caption="Search results" className="min-w-full text-sm rounded-lg overflow-hidden bg-white">
        <TableHeader>
          <TableRow>
            <TableHead>{t("search.col.id", "ID")}</TableHead>
            <TableHead>{t("search.col.project", "Project")}</TableHead>
            <TableHead>{t("search.col.preview", "Preview")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((r) => (
            <TableRow key={r.id} className="border-t last:border-none">
              <TableCell className="font-mono text-xs">
                <Link href={`/projects/${r.project || ""}`}>{r.id}</Link>
              </TableCell>
              <TableCell>{r.project || ""}</TableCell>
              <TableCell>{r.content.slice(0, 40)}</TableCell>
            </TableRow>
          ))}
          {results.length === 0 && (
            <TableRow>
              <TableCell colSpan={3} className="text-center py-4 text-gray-400">
                {t("search.no_results", "No results found.")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
