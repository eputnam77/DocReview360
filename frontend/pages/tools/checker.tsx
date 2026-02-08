// app/tools/checker/page.tsx  (or pages/tools/checker.tsx)
"use client";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { FileInput } from "@/components/ui/file-input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { API } from "@/lib/api";
import { AlertCircle, CheckCircle, Download, FileWarning, UploadCloud } from "lucide-react";
import React, { useState } from "react";

interface CheckResult {
  [key: string]: unknown;
}

interface CheckResponse {
  results: CheckResult;
  downloadToken?: string;
  filename?: string;
  error?: string;
}

export default function CheckerPage() {
  const [result, setResult] = useState<CheckResult | null>(null);
  const [download, setDownload] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<'unknown' | 'connected' | 'disconnected'>('unknown');

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);
    setDownload(null);

    const formData = new FormData(e.currentTarget);
    const apiUrl = API || '/api';

    try {
      console.log(`Submitting to: ${apiUrl}/tools/checker`);
      const res = await fetch(`${apiUrl}/tools/checker`, {
        method: "POST",
        body: formData
      });

      if (res.ok) {
        const data: CheckResponse = await res.json();
        setResult(data.results);
        if (data.downloadToken) {
          setDownload(`${apiUrl}/tools/checker?token=${encodeURIComponent(data.downloadToken)}`);
        } else if (data.filename) {
          setDownload(`/downloads/${data.filename}`);
        }
        setApiStatus('connected');
      } else {
        const errorData = await res.json().catch(() => ({}));
        const errorMessage = errorData.error || `HTTP ${res.status}: ${res.statusText}`;
        setError(`Backend error: ${errorMessage}`);
        setApiStatus('disconnected');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Network error';
      setError(`Connection error: ${errorMessage}`);
      setApiStatus('disconnected');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Document Checker</h1>

      {/* API Status Indicator */}
      {apiStatus !== 'unknown' && (
        <Card className={`max-w-lg ${apiStatus === 'connected' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              {apiStatus === 'connected' ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600" />
              )}
              <span className={`text-sm font-medium ${apiStatus === 'connected' ? 'text-green-800' : 'text-red-800'}`}>
                {apiStatus === 'connected'
                  ? 'Connected to FedStyleValidator backend'
                  : 'Backend connection failed - check configuration'
                }
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Card */}
      <Card className="max-w-lg">
        <CardHeader className="space-y-1">
          <UploadCloud className="h-8 w-8 text-indigo-600" />
          <CardTitle className="text-lg">Upload a document</CardTitle>
          <CardDescription>
            DOC / DOCX only. The checker validates headings, accessibility, and FAA style using FedStyleValidator.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <FileInput
              name="file"
              accept=".doc,.docx"
              required
            />
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? "Running FedStyleValidator checks..." : "Run checks"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <CardTitle className="text-lg font-semibold text-red-800">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700">{error}</p>
            <div className="mt-4 text-sm text-red-600">
              <p><strong>Troubleshooting:</strong></p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Ensure the backend server is running on port 8000</li>
                <li>Check that FedStyleValidator is properly installed</li>
                <li>Verify NEXT_PUBLIC_API_BASE environment variable is set</li>
                <li>Check browser console for detailed error information</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Card */}
      {result && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <FileWarning className="h-6 w-6 text-orange-600" />
            <CardTitle className="text-lg font-semibold">FedStyleValidator Results</CardTitle>
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
