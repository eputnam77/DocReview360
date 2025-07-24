// app/tools/checker/page.tsx  (or pages/tools/checker.tsx)
"use client";

import React, { useState } from "react";
import { API } from "@/lib/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileInput } from "@/components/ui/file-input"; // 👈 Wraps native <input type="file"> with styles*
import { ScrollArea } from "@/components/ui/scroll-area";
import { UploadCloud, FileWarning, Download } from "lucide-react";

interface CheckResult {
  [key: string]: unknown;
}

const DEMO_RESULT: CheckResult = {
  heading: "Missing H2",
  accessibility: "alt text",
};

export default function CheckerPage() {
  const [result, setResult] = useState<CheckResult | null>(null);
  const [download, setDownload] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsLoading(true);

    const formData = new FormData(e.currentTarget);
    try {
      const res = await fetch(`${API}/tools/checker`, { method: "POST", body: formData });

      if (res.ok) {
        const data = await res.json();
        setResult(data.results);
        setDownload(`/downloads/${data.filename}`);
      } else {
        setResult(DEMO_RESULT);
      }
    } catch {
      setResult(DEMO_RESULT);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Document Checker</h1>

      {/* Upload Card */}
      <Card className="max-w-lg">
        <CardHeader className="space-y-1">
          <UploadCloud className="h-8 w-8 text-indigo-600" />
          <CardTitle className="text-lg">Upload a document</CardTitle>
          <CardDescription>
            DOC / DOCX only. The checker validates headings, accessibility, and FAA style.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <FileInput            /* a styled <input type="file"> helper ─ see note below */
              name="file"
              accept=".doc,.docx"
              required
            />
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? "Checking…" : "Run checks"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Results Card */}
      {result && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <FileWarning className="h-6 w-6 text-orange-600" />
            <CardTitle className="text-lg font-semibold">Issues found</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-72 rounded-md border p-2">
              <pre className="whitespace-pre-wrap text-sm">
                {JSON.stringify(result, null, 2)}
              </pre>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Download link */}
      {download && (
        <Button asChild variant="secondary" className="gap-2 max-w-max">
          <a href={download}>
            <Download className="h-4 w-4" />
            Download corrected document
          </a>
        </Button>
      )}
    </div>
  );
}

/* 
 * *If your design system doesn’t include <FileInput>, swap it with:
 *   <input
 *     type="file"
 *     name="file"
 *     accept=".doc,.docx"
 *     className="w-full rounded border border-gray-300 p-2 text-sm
 *                file:mr-4 file:rounded file:border-0 file:bg-indigo-600
 *                file:px-3 file:py-2 file:text-white
 *                hover:file:bg-indigo-700"
 *   />
 */
