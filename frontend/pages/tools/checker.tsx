// pages/tools/checker.tsx
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { authenticatedFetch } from "@/lib/api";
import {
    AlertCircle,
    CheckCircle,
    Download,
    FileText,
    FileWarning,
    Loader2,
    UploadCloud,
} from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";

/* ---------- Types ---------- */

interface CheckResult {
    [key: string]: unknown;
}

interface CheckResponse {
    results: CheckResult;
    downloadToken?: string;
    filename?: string;
    error?: string;
}

interface SystemDocument {
    id: string;
    content?: string;
    doc_type?: string;
    status?: string;
    project?: string;
    project_id?: string;
    editor?: string;
    number?: number;
    public_copy?: boolean;
}

interface QualityResult {
    score: number;
    flags: string[];
}

interface PlainLanguageResult {
    flesch_score: number;
    grade_level: number;
    recommendation: string;
}

interface AcronymIssue {
    acronym: string;
    location?: string;
}

interface StyleIssue {
    issue: string;
    suggestion: string;
    location?: string;
}

interface RegulatoryResult {
    citations: Array<{
        citation: string;
        status: string;
        detail?: string;
    }>;
    summary?: string;
}

interface HeadingIssue {
    heading: string;
    issue: string;
}

interface UnifiedResults {
    quality: QualityResult | null;
    plainLanguage: PlainLanguageResult | null;
    acronyms: AcronymIssue[];
    styleIssues: StyleIssue[];
    regulatory: RegulatoryResult | null;
    headings: HeadingIssue[];
}

/* ---------- Helpers ---------- */

function scoreColor(score: number): string {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.5) return "text-yellow-600";
    return "text-red-600";
}

function scoreBg(score: number): string {
    if (score >= 0.8) return "bg-green-50 border-green-200";
    if (score >= 0.5) return "bg-yellow-50 border-yellow-200";
    return "bg-red-50 border-red-200";
}

function formatSystemDocumentLabel(doc: SystemDocument): string {
    const primary = doc.number ? `Document ${doc.number}` : doc.id;
    const details = [
        doc.project || doc.project_id ? `Project ${doc.project || doc.project_id}` : null,
        doc.doc_type || null,
        doc.editor ? `${doc.editor.toUpperCase()} editor` : null,
        doc.status || null,
        doc.public_copy ? "Public copy" : null,
    ].filter(Boolean);
    return details.length > 0 ? `${primary} - ${details.join(" | ")}` : primary;
}

/* ---------- Component ---------- */

export default function CheckerPage() {
    // Upload mode state
    const [result, setResult] = useState<CheckResult | null>(null);
    const [download, setDownload] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [apiStatus, setApiStatus] = useState<
        "unknown" | "connected" | "disconnected"
    >("unknown");

    // System document mode state
    const [documents, setDocuments] = useState<SystemDocument[]>([]);
    const [selectedDocId, setSelectedDocId] = useState<string>("");
    const [docsLoading, setDocsLoading] = useState(false);
    const [validating, setValidating] = useState(false);
    const [unifiedResults, setUnifiedResults] = useState<UnifiedResults | null>(
        null,
    );
    const [sysError, setSysError] = useState<string | null>(null);
    const [documentAccessNote, setDocumentAccessNote] = useState<string | null>(
        null,
    );

    // Active tab
    const [activeTab, setActiveTab] = useState<string>("upload");

    /* Fetch documents list when switching to system-doc tab */
    const fetchDocuments = useCallback(async () => {
        setDocsLoading(true);
        setSysError(null);
        setDocumentAccessNote(null);
        try {
            let res = await authenticatedFetch(`/documents`);
            let note: string | null = null;
            if (!res.ok && (res.status === 401 || res.status === 403)) {
                const publicRes = await authenticatedFetch(`/documents/public`);
                if (publicRes.ok) {
                    res = publicRes;
                    note =
                        "Showing public system documents only. Sign in to browse private project documents.";
                }
            }
            if (!res.ok) {
                if (res.status === 401 || res.status === 403) {
                    throw new Error("Sign in to browse private system documents.");
                }
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            const data = await res.json();
            // API may return an array or { documents: [...] }
            const docs: SystemDocument[] = Array.isArray(data)
                ? data
                : data.documents ?? [];
            setDocuments(docs);
            setDocumentAccessNote(note);
        } catch (err) {
            const msg =
                err instanceof Error ? err.message : "Failed to load documents";
            setSysError(`Could not fetch documents: ${msg}`);
            setDocuments([]);
        } finally {
            setDocsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (activeTab === "system") {
            fetchDocuments();
        }
    }, [activeTab, fetchDocuments]);

    /* ---------- Upload mode handler ---------- */

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setIsLoading(true);
        setError(null);
        setResult(null);
        setDownload(null);

        const formData = new FormData(e.currentTarget);

        try {
            const res = await authenticatedFetch(`/tools/checker`, {
                method: "POST",
                body: formData,
            });

            if (res.ok) {
                const data: CheckResponse = await res.json();
                setResult(data.results);
                if (data.downloadToken) {
                    setDownload(
                        `/tools/checker?token=${encodeURIComponent(data.downloadToken)}`,
                    );
                } else if (data.filename) {
                    setDownload(`/downloads/${data.filename}`);
                }
                setApiStatus("connected");
            } else {
                const errorData = await res.json().catch(() => ({}));
                const errorMessage =
                    errorData.error ||
                    `HTTP ${res.status}: ${res.statusText}`;
                setError(`Backend error: ${errorMessage}`);
                setApiStatus("disconnected");
            }
        } catch (err) {
            const errorMessage =
                err instanceof Error ? err.message : "Network error";
            setError(`Connection error: ${errorMessage}`);
            setApiStatus("disconnected");
        } finally {
            setIsLoading(false);
        }
    }

    /* ---------- System document validation handler ---------- */

    async function runSystemValidation() {
        if (!selectedDocId) return;

        const doc = documents.find((d) => d.id === selectedDocId);
        if (!doc) {
            setSysError("Selected document not found");
            return;
        }

        const text = doc.content || "";
        if (!text.trim()) {
            setSysError(
                "Selected document has no content to validate. " +
                    "Ensure the document has been uploaded with text content.",
            );
            return;
        }

        setValidating(true);
        setSysError(null);
        setUnifiedResults(null);

        const results: UnifiedResults = {
            quality: null,
            plainLanguage: null,
            acronyms: [],
            styleIssues: [],
            regulatory: null,
            headings: [],
        };

        try {
            // Single unified validation call (Item 48 — replaces three parallel requests)
            const validateRes = await authenticatedFetch(`/documents/validate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
            });

            if (!validateRes.ok) {
                throw new Error(`Validation failed: HTTP ${validateRes.status}`);
            }
            const unified = await validateRes.json();

            // Parse preflight section
            const pf = unified.preflight ?? {};
            results.acronyms = (pf.acronyms || pf.undefined_acronyms || []).map(
                (a: string | AcronymIssue) =>
                    typeof a === "string" ? { acronym: a } : a,
            );
            results.headings = (pf.headings || pf.heading_issues || []).map(
                (h: string | HeadingIssue) =>
                    typeof h === "string" ? { heading: h, issue: "Issue detected" } : h,
            );
            results.styleIssues = (pf.style || pf.style_issues || []).map(
                (s: string | StyleIssue) =>
                    typeof s === "string" ? { issue: s, suggestion: "" } : s,
            );
            if (pf.plain_language || pf.readability) {
                const pl = pf.plain_language || pf.readability;
                results.plainLanguage = {
                    flesch_score: pl.flesch_score ?? pl.flesch ?? 0,
                    grade_level: pl.grade_level ?? pl.grade ?? 0,
                    recommendation: pl.recommendation ?? pl.summary ?? "",
                };
            }

            // Parse regulatory section
            const reg = unified.regulatory ?? {};
            if (Object.keys(reg).length > 0) {
                results.regulatory = {
                    citations: reg.citations || reg.results || [],
                    summary: reg.summary,
                };
            }

            // Parse quality section
            const q = unified.quality ?? {};
            if (q.score != null || q.quality_score != null) {
                results.quality = {
                    score: q.score ?? q.quality_score ?? 0,
                    flags: q.flags || q.issues || [],
                };
            }

            setUnifiedResults(results);
        } catch (err) {
            const msg =
                err instanceof Error ? err.message : "Validation failed";
            setSysError(msg);
        } finally {
            setValidating(false);
        }
    }

    /* ---------- Render ---------- */

    return (
        <div className="p-8 space-y-8 max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold">Document Checker</h1>
            <p className="text-gray-500 text-sm">
                Validate documents against federal style guidelines, plain
                language standards, and regulatory requirements.
            </p>

            {/* API Status Indicator */}
            {apiStatus !== "unknown" && (
                <Card
                    className={`${apiStatus === "connected" ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}
                >
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2">
                            {apiStatus === "connected" ? (
                                <CheckCircle className="h-5 w-5 text-green-600" />
                            ) : (
                                <AlertCircle className="h-5 w-5 text-red-600" />
                            )}
                            <span
                                className={`text-sm font-medium ${apiStatus === "connected" ? "text-green-800" : "text-red-800"}`}
                            >
                                {apiStatus === "connected"
                                    ? "Connected to FedStyleValidator backend"
                                    : "Backend connection failed - check configuration"}
                            </span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Mode tabs */}
            <Tabs
                defaultValue="upload"
                value={activeTab}
                onValueChange={setActiveTab}
            >
                <TabsList>
                    <TabsTrigger value="upload">
                        <span className="flex items-center gap-2">
                            <UploadCloud className="h-4 w-4" />
                            Upload File
                        </span>
                    </TabsTrigger>
                    <TabsTrigger value="system">
                        <span className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            System Document
                        </span>
                    </TabsTrigger>
                </TabsList>

                {/* ===== Upload File Tab ===== */}
                <TabsContent value="upload">
                    <Card className="max-w-lg">
                        <CardHeader className="space-y-1">
                            <UploadCloud className="h-8 w-8 text-indigo-600" />
                            <CardTitle className="text-lg">
                                Upload a document
                            </CardTitle>
                            <CardDescription>
                                DOC / DOCX only. The checker validates headings,
                                accessibility, and FAA style using
                                FedStyleValidator.
                            </CardDescription>
                        </CardHeader>

                        <CardContent>
                            <form
                                onSubmit={handleSubmit}
                                className="space-y-4"
                            >
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
                                    {isLoading
                                        ? "Running FedStyleValidator checks..."
                                        : "Run checks"}
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Error Display */}
                    {error && (
                        <Card className="border-red-200 bg-red-50 mt-6">
                            <CardHeader className="flex flex-row items-center gap-3 pb-2">
                                <AlertCircle className="h-6 w-6 text-red-600" />
                                <CardTitle className="text-lg font-semibold text-red-800">
                                    Error
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-red-700">{error}</p>
                                <div className="mt-4 text-sm text-red-600">
                                    <p>
                                        <strong>Troubleshooting:</strong>
                                    </p>
                                    <ul className="list-disc list-inside mt-2 space-y-1">
                                        <li>
                                            Ensure the backend server is running
                                            on port 8000
                                        </li>
                                        <li>
                                            Check that FedStyleValidator is
                                            properly installed
                                        </li>
                                        <li>
                                            Verify NEXT_PUBLIC_API_BASE
                                            environment variable is set
                                        </li>
                                        <li>
                                            Check browser console for detailed
                                            error information
                                        </li>
                                    </ul>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Upload Results Card */}
                    {result && (
                        <Card className="mt-6">
                            <CardHeader className="flex flex-row items-center gap-3 pb-2">
                                <FileWarning className="h-6 w-6 text-orange-600" />
                                <CardTitle className="text-lg font-semibold">
                                    FedStyleValidator Results
                                </CardTitle>
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
                        <Button
                            asChild
                            variant="secondary"
                            className="gap-2 max-w-max mt-4"
                        >
                            <a href={download}>
                                <Download className="h-4 w-4" />
                                Download corrected document
                            </a>
                        </Button>
                    )}
                </TabsContent>

                {/* ===== System Document Tab ===== */}
                <TabsContent value="system">
                    <Card className="max-w-lg">
                        <CardHeader className="space-y-1">
                            <FileText className="h-8 w-8 text-indigo-600" />
                            <CardTitle className="text-lg">
                                Select a system document
                            </CardTitle>
                            <CardDescription>
                                Choose a document from the system to run a
                                unified validation report including quality,
                                style, regulatory, and readability checks.
                            </CardDescription>
                        </CardHeader>

                        <CardContent className="space-y-4">
                            {docsLoading ? (
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Loading documents...
                                </div>
                            ) : (
                                <>
                                    <div className="space-y-2">
                                        <label
                                            htmlFor="doc-select"
                                            className="text-sm font-medium text-gray-700"
                                        >
                                            Document
                                        </label>
                                        {documentAccessNote && (
                                            <p className="text-xs text-amber-700">
                                                {documentAccessNote}
                                            </p>
                                        )}
                                        <select
                                            id="doc-select"
                                            value={selectedDocId}
                                            onChange={(e) =>
                                                setSelectedDocId(e.target.value)
                                            }
                                            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                        >
                                            <option value="">
                                                -- Select a document --
                                            </option>
                                            {documents.map((doc) => (
                                                <option
                                                    key={doc.id}
                                                    value={doc.id}
                                                >
                                                    {formatSystemDocumentLabel(doc)}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {documents.length === 0 && !sysError && (
                                        <p className="text-sm text-gray-500">
                                            No documents found. Upload a
                                            document first or check your
                                            authentication.
                                        </p>
                                    )}

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={runSystemValidation}
                                            disabled={
                                                !selectedDocId || validating
                                            }
                                            className="flex-1"
                                        >
                                            {validating ? (
                                                <>
                                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                    Running validation...
                                                </>
                                            ) : (
                                                "Run Validation"
                                            )}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={fetchDocuments}
                                            disabled={docsLoading}
                                            title="Refresh document list"
                                        >
                                            Refresh
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    {/* System doc error */}
                    {sysError && (
                        <Card className="border-red-200 bg-red-50 mt-6">
                            <CardHeader className="flex flex-row items-center gap-3 pb-2">
                                <AlertCircle className="h-6 w-6 text-red-600" />
                                <CardTitle className="text-lg font-semibold text-red-800">
                                    Error
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-red-700">{sysError}</p>
                            </CardContent>
                        </Card>
                    )}

                    {/* ===== Unified Results ===== */}
                    {unifiedResults && (
                        <div className="mt-6 space-y-4">
                            <h2 className="text-lg font-semibold flex items-center gap-2">
                                <FileWarning className="h-5 w-5 text-orange-600" />
                                Validation Report
                            </h2>

                            {/* Quality Score Card */}
                            {unifiedResults.quality && (
                                <Card
                                    className={scoreBg(
                                        unifiedResults.quality.score,
                                    )}
                                >
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">
                                            Quality Score
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex items-baseline gap-3 mb-3">
                                            <span
                                                className={`text-3xl font-bold ${scoreColor(unifiedResults.quality.score)}`}
                                            >
                                                {(
                                                    unifiedResults.quality
                                                        .score * 100
                                                ).toFixed(0)}
                                                %
                                            </span>
                                            <span className="text-sm text-gray-500">
                                                (
                                                {unifiedResults.quality.score.toFixed(
                                                    2,
                                                )}
                                                )
                                            </span>
                                        </div>
                                        {unifiedResults.quality.flags.length >
                                        0 ? (
                                            <ul className="space-y-1">
                                                {unifiedResults.quality.flags.map(
                                                    (flag, i) => (
                                                        <li
                                                            key={i}
                                                            className="text-sm flex items-start gap-2"
                                                        >
                                                            <AlertCircle className="h-4 w-4 text-orange-500 mt-0.5 shrink-0" />
                                                            {flag}
                                                        </li>
                                                    ),
                                                )}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-green-700">
                                                No quality flags raised.
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Plain Language Card */}
                            {unifiedResults.plainLanguage && (
                                <Card>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">
                                            Plain Language
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 gap-4 mb-3">
                                            <div>
                                                <p className="text-xs text-gray-500 uppercase tracking-wide">
                                                    Flesch Score
                                                </p>
                                                <p className="text-xl font-semibold">
                                                    {unifiedResults.plainLanguage.flesch_score.toFixed(
                                                        1,
                                                    )}
                                                </p>
                                            </div>
                                            <div>
                                                <p className="text-xs text-gray-500 uppercase tracking-wide">
                                                    Grade Level
                                                </p>
                                                <p className="text-xl font-semibold">
                                                    {unifiedResults.plainLanguage.grade_level.toFixed(
                                                        1,
                                                    )}
                                                </p>
                                            </div>
                                        </div>
                                        {unifiedResults.plainLanguage
                                            .recommendation && (
                                            <p className="text-sm text-gray-700 bg-gray-50 rounded p-2">
                                                {
                                                    unifiedResults
                                                        .plainLanguage
                                                        .recommendation
                                                }
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Acronym Issues Card */}
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base">
                                        Acronym Issues
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {unifiedResults.acronyms.length > 0 ? (
                                        <ul className="space-y-1">
                                            {unifiedResults.acronyms.map(
                                                (a, i) => (
                                                    <li
                                                        key={i}
                                                        className="text-sm flex items-start gap-2"
                                                    >
                                                        <AlertCircle className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
                                                        <span>
                                                            <strong>
                                                                {a.acronym}
                                                            </strong>
                                                            {a.location
                                                                ? ` - ${a.location}`
                                                                : " - undefined acronym"}
                                                        </span>
                                                    </li>
                                                ),
                                            )}
                                        </ul>
                                    ) : (
                                        <p className="text-sm text-green-700">
                                            No undefined acronyms found.
                                        </p>
                                    )}
                                </CardContent>
                            </Card>

                            {/* Style Issues Card */}
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base">
                                        Style Issues
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {unifiedResults.styleIssues.length > 0 ? (
                                        <ul className="space-y-2">
                                            {unifiedResults.styleIssues.map(
                                                (s, i) => (
                                                    <li
                                                        key={i}
                                                        className="text-sm border-l-2 border-orange-300 pl-3"
                                                    >
                                                        <p className="font-medium">
                                                            {s.issue}
                                                        </p>
                                                        {s.suggestion && (
                                                            <p className="text-gray-500 mt-0.5">
                                                                Suggestion:{" "}
                                                                {s.suggestion}
                                                            </p>
                                                        )}
                                                    </li>
                                                ),
                                            )}
                                        </ul>
                                    ) : (
                                        <p className="text-sm text-green-700">
                                            No style issues detected.
                                        </p>
                                    )}
                                </CardContent>
                            </Card>

                            {/* Regulatory Citations Card */}
                            {unifiedResults.regulatory && (
                                <Card>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">
                                            Regulatory Citations
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        {unifiedResults.regulatory.summary && (
                                            <p className="text-sm text-gray-700 mb-3">
                                                {
                                                    unifiedResults.regulatory
                                                        .summary
                                                }
                                            </p>
                                        )}
                                        {unifiedResults.regulatory.citations
                                            .length > 0 ? (
                                            <ul className="space-y-2">
                                                {unifiedResults.regulatory.citations.map(
                                                    (c, i) => (
                                                        <li
                                                            key={i}
                                                            className="text-sm flex items-start gap-2"
                                                        >
                                                            {c.status ===
                                                                "valid" ||
                                                            c.status ===
                                                                "pass" ? (
                                                                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                                                            ) : (
                                                                <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                                                            )}
                                                            <span>
                                                                <strong>
                                                                    {
                                                                        c.citation
                                                                    }
                                                                </strong>
                                                                {" - "}
                                                                {c.status}
                                                                {c.detail
                                                                    ? `: ${c.detail}`
                                                                    : ""}
                                                            </span>
                                                        </li>
                                                    ),
                                                )}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-gray-500">
                                                No regulatory citations found in
                                                document.
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Heading Structure Card */}
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base">
                                        Heading Structure
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {unifiedResults.headings.length > 0 ? (
                                        <ul className="space-y-2">
                                            {unifiedResults.headings.map(
                                                (h, i) => (
                                                    <li
                                                        key={i}
                                                        className="text-sm border-l-2 border-yellow-300 pl-3"
                                                    >
                                                        <p className="font-medium">
                                                            {h.heading}
                                                        </p>
                                                        <p className="text-gray-500 mt-0.5">
                                                            {h.issue}
                                                        </p>
                                                    </li>
                                                ),
                                            )}
                                        </ul>
                                    ) : (
                                        <p className="text-sm text-green-700">
                                            No heading structure issues found.
                                        </p>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
