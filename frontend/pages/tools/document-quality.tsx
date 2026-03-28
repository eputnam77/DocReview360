// pages/tools/document-quality.tsx
//
// Document Quality Checker — unified surface for all validation engines.
// Tab 1: Federal Style Validator (primary engine, built-in)
// Tab 2: Additional Engines — reserved for future integrations (Coming Soon)
//
// UX improvements (FSV_INTEGRATION_UX_TASKS.md):
//   DR-FSV-2: Pass X-FSV-Theme: light header so future iframe embeds use light surface
//   DR-FSV-3: Severity colors aligned with DocReview360's system (red-600/amber-600/blue-600)
//   DR-FSV-4: Zero-issues success state with green CheckCircle banner
//   DR-FSV-5: Structured findings with severity badge, style authority, and how-to-fix hint
//   DR-FSV-6: Per-category collapsible sections with count badges
//   DR-FSV-7: Loading skeleton while FSV is processing the document
//   DR-FSV-8: Prominent FSV-unavailable banner when GET /fsv/status is unhealthy
//   DR-FSV-10: Accept document_id query param, auto-select document in system-doc tab
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
import { useUserStore } from "@/state/user";
import {
    AlertCircle,
    AlertTriangle,
    CheckCircle,
    Clock,
    Download,
    FileText,
    FileWarning,
    Info,
    Loader2,
    Shield,
    UploadCloud,
    XCircle,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/router";
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

/** Normalized finding from the upload-tab checker response (DR-FSV-5) */
interface Finding {
    severity: "error" | "warning" | "info";
    message: string;
    authority?: string;
    fix?: string;
    category: string;
}

type FsvServiceStatus = "checking" | "available" | "unavailable" | "unknown";

/* ---------- Color helpers (DR-FSV-3) ---------- */

function scoreColor(score: number): string {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.5) return "text-amber-600";   // DR-FSV-3: aligned to DocReview360 amber token
    return "text-red-600";
}

function scoreBg(score: number): string {
    if (score >= 0.8) return "bg-green-50 border-green-200";
    if (score >= 0.5) return "bg-amber-50 border-amber-200"; // DR-FSV-3: aligned to DocReview360 amber token
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

/* ---------- Finding parser (DR-FSV-5) ---------- */

function parseFindingsFromCheckResult(result: CheckResult): Finding[] {
    const findings: Finding[] = [];
    const r = result as Record<string, unknown>;

    // Generic issue arrays at the top level
    const genericKeys: Array<[string, "error" | "warning" | "info", string]> = [
        ["issues", "warning", "General"],
        ["errors", "error", "General"],
        ["findings", "warning", "General"],
        ["violations", "error", "General"],
    ];
    for (const [key, defaultSeverity, defaultCategory] of genericKeys) {
        const arr = Array.isArray(r[key]) ? (r[key] as unknown[]) : [];
        for (const item of arr) {
            if (typeof item === "string") {
                findings.push({ severity: defaultSeverity, message: item, category: defaultCategory });
            } else if (item && typeof item === "object") {
                const obj = item as Record<string, unknown>;
                findings.push({
                    severity: (obj.severity as "error" | "warning" | "info") ?? defaultSeverity,
                    message:
                        typeof obj.message === "string" ? obj.message :
                        typeof obj.issue === "string" ? obj.issue :
                        JSON.stringify(obj),
                    authority:
                        typeof obj.authority === "string" ? obj.authority :
                        typeof obj.source === "string" ? obj.source :
                        typeof obj.rule === "string" ? obj.rule :
                        undefined,
                    fix:
                        typeof obj.fix === "string" ? obj.fix :
                        typeof obj.suggestion === "string" ? obj.suggestion :
                        typeof obj.recommendation === "string" ? obj.recommendation :
                        undefined,
                    category:
                        typeof obj.category === "string" ? obj.category :
                        typeof obj.type === "string" ? obj.type :
                        defaultCategory,
                });
            }
        }
    }

    // Heading issues
    const headings = Array.isArray(r.headings) ? (r.headings as unknown[]) : [];
    for (const h of headings) {
        if (typeof h === "string") {
            findings.push({ severity: "warning", message: h, category: "Heading" });
        } else if (h && typeof h === "object") {
            const obj = h as Record<string, unknown>;
            findings.push({
                severity: "warning",
                message:
                    typeof obj.issue === "string" ? obj.issue :
                    typeof obj.message === "string" ? obj.message :
                    `Heading issue: ${obj.heading ?? ""}`,
                authority: typeof obj.authority === "string" ? obj.authority : "FAA Order 1320.46D §3",
                fix:
                    typeof obj.fix === "string" ? obj.fix :
                    typeof obj.suggestion === "string" ? obj.suggestion :
                    "Ensure headings follow document hierarchy (H1 > H2 > H3) without skipping levels.",
                category: "Heading",
            });
        }
    }

    // Acronym issues
    const acronymArr: unknown[] = Array.isArray(r.acronyms) ? (r.acronyms as unknown[]) :
        Array.isArray(r.undefined_acronyms) ? (r.undefined_acronyms as unknown[]) : [];
    for (const a of acronymArr) {
        if (typeof a === "string") {
            findings.push({
                severity: "warning",
                message: `Undefined acronym: ${a}`,
                authority: "FAA Order 1320.46D §4.2",
                fix: "Define the acronym on first use, e.g. 'Federal Aviation Administration (FAA)'.",
                category: "Acronym",
            });
        } else if (a && typeof a === "object") {
            const obj = a as Record<string, unknown>;
            findings.push({
                severity: "warning",
                message: `Undefined acronym: ${obj.acronym}${obj.location ? ` (${obj.location})` : ""}`,
                authority: "FAA Order 1320.46D §4.2",
                fix:
                    typeof obj.fix === "string" ? obj.fix :
                    "Define the acronym on first use, e.g. 'Federal Aviation Administration (FAA)'.",
                category: "Acronym",
            });
        }
    }

    // Style issues
    const styleArr: unknown[] = Array.isArray(r.style) ? (r.style as unknown[]) :
        Array.isArray(r.style_issues) ? (r.style_issues as unknown[]) : [];
    for (const s of styleArr) {
        if (typeof s === "string") {
            findings.push({ severity: "error", message: s, authority: "AP Style Guide", category: "Style" });
        } else if (s && typeof s === "object") {
            const obj = s as Record<string, unknown>;
            findings.push({
                severity: "error",
                message:
                    typeof obj.issue === "string" ? obj.issue :
                    typeof obj.message === "string" ? obj.message :
                    String(obj),
                authority: typeof obj.authority === "string" ? obj.authority : "AP Style Guide",
                fix:
                    typeof obj.suggestion === "string" ? obj.suggestion :
                    typeof obj.fix === "string" ? obj.fix :
                    undefined,
                category: "Style",
            });
        }
    }

    return findings;
}

function groupFindingsByCategory(findings: Finding[]): Map<string, Finding[]> {
    const map = new Map<string, Finding[]>();
    for (const f of findings) {
        const list = map.get(f.category) ?? [];
        list.push(f);
        map.set(f.category, list);
    }
    return map;
}

/* ---------- Sub-components ---------- */

/** DR-FSV-7: Loading skeleton placeholder rows */
function LoadingSkeleton() {
    return (
        <div className="space-y-3 mt-6" aria-label="Loading results" aria-busy="true">
            {[80, 65, 90, 55].map((w, i) => (
                <div
                    key={i}
                    className="h-4 rounded bg-gray-200 animate-pulse"
                    style={{ width: `${w}%` }}
                />
            ))}
        </div>
    );
}

/** DR-FSV-5: Severity badge */
function SeverityBadge({ severity }: { severity: "error" | "warning" | "info" }) {
    if (severity === "error") {
        return (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-xs font-semibold text-red-600">
                <XCircle className="h-3 w-3" />
                Error
            </span>
        );
    }
    if (severity === "warning") {
        return (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-xs font-semibold text-amber-600">
                <AlertTriangle className="h-3 w-3" />
                Warning
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs font-semibold text-blue-600">
            <Info className="h-3 w-3" />
            Info
        </span>
    );
}

/** DR-FSV-4: Zero-issues success banner */
function SuccessBanner({ categories }: { categories: string[] }) {
    return (
        <Card className="border-green-200 bg-green-50">
            <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                    <CheckCircle className="h-6 w-6 text-green-600 shrink-0 mt-0.5" />
                    <div>
                        <p className="font-semibold text-green-800 text-base">No style issues found</p>
                        <p className="text-sm text-green-700 mt-1">
                            The document passed all active check categories
                            {categories.length > 0 ? `: ${categories.join(", ")}.` : "."}
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

/** DR-FSV-6: Collapsible section wrapper with count badge */
function CollapsibleSection({
    title,
    count,
    defaultOpen = false,
    children,
}: {
    title: string;
    count: number;
    defaultOpen?: boolean;
    children: React.ReactNode;
}) {
    return (
        <details open={defaultOpen} className="group">
            <summary className="flex cursor-pointer select-none items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                <span>{title}</span>
                <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        count === 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}
                >
                    {count} {count === 1 ? "issue" : "issues"}
                </span>
            </summary>
            <div className="mt-2">{children}</div>
        </details>
    );
}

/** DR-FSV-8: FSV service unavailable banner */
function FsvUnavailableBanner({ isAdmin }: { isAdmin: boolean }) {
    return (
        <Card className="border-amber-200 bg-amber-50">
            <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <p className="font-semibold text-amber-800">
                            Federal Style Validator service is currently unavailable.
                        </p>
                        <p className="text-sm text-amber-700 mt-1">
                            Contact your administrator or try again later.
                            {isAdmin && (
                                <>
                                    {" "}
                                    <Link
                                        href="/tools"
                                        className="underline font-medium text-amber-800 hover:text-amber-900"
                                    >
                                        Reconfigure the FSV service URL
                                    </Link>{" "}
                                    in admin settings.
                                </>
                            )}
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

/** DR-FSV-5, DR-FSV-6: Grouped structured findings from upload result */
function FindingsDisplay({ findings }: { findings: Finding[] }) {
    if (findings.length === 0) {
        return (
            <SuccessBanner categories={["Headings", "Acronyms", "Style", "Accessibility"]} />
        );
    }

    const grouped = groupFindingsByCategory(findings);
    const CATEGORY_ORDER = ["Style", "Heading", "Acronym", "General"];
    const sortedCategories = [
        ...CATEGORY_ORDER.filter((c) => grouped.has(c)),
        ...[...grouped.keys()].filter((k) => !CATEGORY_ORDER.includes(k)),
    ];

    return (
        <div className="space-y-3">
            <p className="text-sm text-gray-500">
                {findings.length} {findings.length === 1 ? "issue" : "issues"} across{" "}
                {sortedCategories.length} {sortedCategories.length === 1 ? "category" : "categories"}.
            </p>
            {sortedCategories.map((category) => {
                const items = grouped.get(category) ?? [];
                return (
                    <CollapsibleSection
                        key={category}
                        title={category}
                        count={items.length}
                        defaultOpen={items.length > 0}
                    >
                        <ul className="space-y-3 py-1">
                            {items.map((f, i) => (
                                <li
                                    key={i}
                                    className="rounded-lg border border-gray-100 bg-white p-3 space-y-1.5"
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <SeverityBadge severity={f.severity} />
                                        {f.authority && (
                                            <span className="text-xs text-gray-400 font-mono">
                                                {f.authority}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-gray-800">{f.message}</p>
                                    {f.fix && (
                                        <div className="rounded bg-blue-50 border border-blue-100 px-2 py-1.5">
                                            <p className="text-xs font-semibold text-blue-700">How to fix</p>
                                            <p className="text-xs text-blue-700 mt-0.5">{f.fix}</p>
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </CollapsibleSection>
                );
            })}
        </div>
    );
}

/** Inline How-to-fix block reused in system-doc results (DR-FSV-5) */
function HowToFix({ text }: { text: string }) {
    return (
        <div className="rounded bg-blue-50 border border-blue-100 px-2 py-1.5 mt-1.5">
            <p className="text-xs font-semibold text-blue-700">How to fix</p>
            <p className="text-xs text-blue-700 mt-0.5">{text}</p>
        </div>
    );
}

/* ---------- Federal Style Validator Panel ---------- */

function FederalStyleValidatorPanel() {
    const router = useRouter();
    const isAdmin = useUserStore((s) => s.isAdmin);

    // Upload mode state
    const [result, setResult] = useState<CheckResult | null>(null);
    const [parsedFindings, setParsedFindings] = useState<Finding[]>([]);
    const [download, setDownload] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [apiStatus, setApiStatus] = useState<"unknown" | "connected" | "disconnected">("unknown");

    // DR-FSV-8: FSV service health state
    const [fsvStatus, setFsvStatus] = useState<FsvServiceStatus>("checking");

    // System document mode state
    const [documents, setDocuments] = useState<SystemDocument[]>([]);
    const [selectedDocId, setSelectedDocId] = useState<string>("");
    const [docsLoading, setDocsLoading] = useState(false);
    const [validating, setValidating] = useState(false);
    const [unifiedResults, setUnifiedResults] = useState<UnifiedResults | null>(null);
    const [sysError, setSysError] = useState<string | null>(null);
    const [documentAccessNote, setDocumentAccessNote] = useState<string | null>(null);

    // Active sub-tab
    const [activeTab, setActiveTab] = useState<string>("upload");

    /* DR-FSV-8: Probe FSV health on mount */
    useEffect(() => {
        authenticatedFetch("/fsv/status")
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (!data) { setFsvStatus("unknown"); return; }
                setFsvStatus(data.reachable ? "available" : data.configured ? "unavailable" : "unknown");
            })
            .catch(() => setFsvStatus("unknown"));
    }, []);

    /* DR-FSV-10: Auto-select document from query param */
    useEffect(() => {
        const qid = router.query.document_id as string | undefined;
        if (qid) {
            setActiveTab("system");
            setSelectedDocId(qid);
        }
    }, [router.query.document_id]);

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
                    note = "Showing public system documents only. Sign in to browse private project documents.";
                }
            }
            if (!res.ok) {
                if (res.status === 401 || res.status === 403) {
                    throw new Error("Sign in to browse private system documents.");
                }
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            const data = await res.json();
            const docs: SystemDocument[] = Array.isArray(data) ? data : data.documents ?? [];
            setDocuments(docs);
            setDocumentAccessNote(note);
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to load documents";
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

    /* Upload handler */
    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setIsLoading(true);
        setError(null);
        setResult(null);
        setParsedFindings([]);
        setDownload(null);

        const formData = new FormData(e.currentTarget);
        // DR-FSV-2: Append theme=light so FSV renders on light surface when embedded
        formData.append("theme", "light");

        try {
            const res = await authenticatedFetch(`/tools/checker`, {
                method: "POST",
                body: formData,
                // DR-FSV-2: Header for non-form callers (e.g. future iframe embed)
                headers: { "X-FSV-Theme": "light" },
            });

            if (res.ok) {
                const data: CheckResponse = await res.json();
                setResult(data.results);
                setParsedFindings(parseFindingsFromCheckResult(data.results));
                if (data.downloadToken) {
                    setDownload(`/tools/checker?token=${encodeURIComponent(data.downloadToken)}`);
                } else if (data.filename) {
                    setDownload(`/downloads/${data.filename}`);
                }
                setApiStatus("connected");
            } else {
                const errorData = await res.json().catch(() => ({}));
                const errorMessage =
                    (errorData as { error?: string }).error ||
                    `HTTP ${res.status}: ${res.statusText}`;
                setError(`Backend error: ${errorMessage}`);
                setApiStatus("disconnected");
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Network error";
            setError(`Connection error: ${errorMessage}`);
            setApiStatus("disconnected");
        } finally {
            setIsLoading(false);
        }
    }

    /* System document validation handler */
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
            const validateRes = await authenticatedFetch(`/documents/validate`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-FSV-Theme": "light" },
                body: JSON.stringify({ text }),
            });

            if (!validateRes.ok) {
                throw new Error(`Validation failed: HTTP ${validateRes.status}`);
            }
            const unified = await validateRes.json();

            const pf = (unified as { preflight?: Record<string, unknown> }).preflight ?? {};
            results.acronyms = (
                (pf.acronyms as unknown[] | undefined) ||
                (pf.undefined_acronyms as unknown[] | undefined) ||
                []
            ).map((a: unknown) =>
                typeof a === "string" ? { acronym: a } : (a as AcronymIssue),
            );
            results.headings = (
                (pf.headings as unknown[] | undefined) ||
                (pf.heading_issues as unknown[] | undefined) ||
                []
            ).map((h: unknown) =>
                typeof h === "string"
                    ? { heading: h, issue: "Issue detected" }
                    : (h as HeadingIssue),
            );
            results.styleIssues = (
                (pf.style as unknown[] | undefined) ||
                (pf.style_issues as unknown[] | undefined) ||
                []
            ).map((s: unknown) =>
                typeof s === "string" ? { issue: s, suggestion: "" } : (s as StyleIssue),
            );
            if (pf.plain_language || pf.readability) {
                const pl = (pf.plain_language || pf.readability) as Record<string, unknown>;
                results.plainLanguage = {
                    flesch_score: (pl.flesch_score as number) ?? (pl.flesch as number) ?? 0,
                    grade_level: (pl.grade_level as number) ?? (pl.grade as number) ?? 0,
                    recommendation: (pl.recommendation as string) ?? (pl.summary as string) ?? "",
                };
            }

            const reg = (unified as { regulatory?: Record<string, unknown> }).regulatory ?? {};
            if (Object.keys(reg).length > 0) {
                results.regulatory = {
                    citations:
                        (reg.citations as RegulatoryResult["citations"]) ||
                        (reg.results as RegulatoryResult["citations"]) ||
                        [],
                    summary: reg.summary as string | undefined,
                };
            }

            const q = (unified as { quality?: Record<string, unknown> }).quality ?? {};
            if (q.score != null || q.quality_score != null) {
                results.quality = {
                    score: (q.score as number) ?? (q.quality_score as number) ?? 0,
                    flags: (q.flags as string[]) || (q.issues as string[]) || [],
                };
            }

            setUnifiedResults(results);
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Validation failed";
            setSysError(msg);
        } finally {
            setValidating(false);
        }
    }

    /* DR-FSV-4: Count all issues in unified results */
    function totalIssueCount(r: UnifiedResults): number {
        return (
            r.acronyms.length +
            r.styleIssues.length +
            r.headings.length +
            (r.quality?.flags.length ?? 0) +
            (r.regulatory?.citations.filter(
                (c) => c.status !== "valid" && c.status !== "pass",
            ).length ?? 0)
        );
    }

    /* DR-FSV-4: Which check categories ran */
    function ranCategories(r: UnifiedResults): string[] {
        const cats: string[] = [];
        if (r.quality) cats.push("Quality");
        if (r.plainLanguage) cats.push("Plain Language");
        cats.push("Acronyms", "Style", "Headings");
        if (r.regulatory) cats.push("Regulatory");
        return cats;
    }

    return (
        <div className="space-y-6">
            {/* Engine info banner */}
            <div className="flex items-center gap-2 rounded-lg bg-indigo-50 border border-indigo-200 px-4 py-3">
                <Shield className="h-5 w-5 text-indigo-600 shrink-0" />
                <p className="text-sm text-indigo-800">
                    <span className="font-semibold">Federal Style Validator</span> — checks
                    FAA/DoD style, plain language, acronyms, regulatory references, readability,
                    and accessibility compliance.
                </p>
            </div>

            {/* DR-FSV-8: Unavailable banner */}
            {fsvStatus === "unavailable" && <FsvUnavailableBanner isAdmin={isAdmin} />}

            {/* API Status Indicator (upload feedback) */}
            {apiStatus !== "unknown" && (
                <Card
                    className={
                        apiStatus === "connected"
                            ? "border-green-200 bg-green-50"
                            : "border-red-200 bg-red-50"
                    }
                >
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2">
                            {apiStatus === "connected" ? (
                                <CheckCircle className="h-5 w-5 text-green-600" />
                            ) : (
                                <AlertCircle className="h-5 w-5 text-red-600" />
                            )}
                            <span
                                className={`text-sm font-medium ${
                                    apiStatus === "connected" ? "text-green-800" : "text-red-800"
                                }`}
                            >
                                {apiStatus === "connected"
                                    ? "Connected to Federal Style Validator backend"
                                    : "Backend connection failed — check configuration"}
                            </span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Mode tabs: Upload File vs System Document */}
            <Tabs defaultValue="upload" value={activeTab} onValueChange={setActiveTab}>
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
                            <CardTitle className="text-lg">Upload a document</CardTitle>
                            <CardDescription>
                                DOC / DOCX only. The Federal Style Validator checks headings,
                                accessibility, FAA/DoD style rules, plain language, and undefined
                                acronyms.
                            </CardDescription>
                        </CardHeader>

                        <CardContent>
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <FileInput name="file" accept=".doc,.docx" required />
                                <Button type="submit" className="w-full" disabled={isLoading}>
                                    {isLoading
                                        ? "Running Federal Style Validator checks..."
                                        : "Run FSV checks"}
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* DR-FSV-7: Loading skeleton */}
                    {isLoading && <LoadingSkeleton />}

                    {/* Error */}
                    {error && (
                        <Card className="border-red-200 bg-red-50 mt-6">
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
                                        <li>Check that Federal Style Validator is properly installed</li>
                                        <li>Verify NEXT_PUBLIC_API_BASE environment variable is set</li>
                                        <li>Check browser console for detailed error information</li>
                                    </ul>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* DR-FSV-4/5/6: Structured Upload Results */}
                    {result && !isLoading && (
                        <Card className="mt-6">
                            <CardHeader className="flex flex-row items-center gap-3 pb-2">
                                {parsedFindings.length === 0 ? (
                                    <CheckCircle className="h-6 w-6 text-green-600" />
                                ) : (
                                    <FileWarning className="h-6 w-6 text-amber-600" />
                                )}
                                <CardTitle className="text-lg font-semibold">
                                    Federal Style Validator Results
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <FindingsDisplay findings={parsedFindings} />
                            </CardContent>
                        </Card>
                    )}

                    {/* Download link */}
                    {download && (
                        <Button asChild variant="secondary" className="gap-2 max-w-max mt-4">
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
                            <CardTitle className="text-lg">Select a system document</CardTitle>
                            <CardDescription>
                                Choose a document from the system to run a unified validation
                                report including quality, style, regulatory, and readability checks.
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
                                            <p className="text-xs text-amber-700">{documentAccessNote}</p>
                                        )}
                                        <select
                                            id="doc-select"
                                            value={selectedDocId}
                                            onChange={(e) => setSelectedDocId(e.target.value)}
                                            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                        >
                                            <option value="">-- Select a document --</option>
                                            {documents.map((doc) => (
                                                <option key={doc.id} value={doc.id}>
                                                    {formatSystemDocumentLabel(doc)}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {documents.length === 0 && !sysError && (
                                        <p className="text-sm text-gray-500">
                                            No documents found. Upload a document first or check your authentication.
                                        </p>
                                    )}

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={runSystemValidation}
                                            disabled={!selectedDocId || validating}
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

                    {/* DR-FSV-7: Loading skeleton for system doc validation */}
                    {validating && <LoadingSkeleton />}

                    {/* System doc error */}
                    {sysError && (
                        <Card className="border-red-200 bg-red-50 mt-6">
                            <CardHeader className="flex flex-row items-center gap-3 pb-2">
                                <AlertCircle className="h-6 w-6 text-red-600" />
                                <CardTitle className="text-lg font-semibold text-red-800">Error</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-red-700">{sysError}</p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Unified Results */}
                    {unifiedResults && !validating && (
                        <div className="mt-6 space-y-4">
                            <h2 className="text-lg font-semibold flex items-center gap-2">
                                <FileWarning className="h-5 w-5 text-indigo-600" />
                                Federal Style Validator Report
                            </h2>

                            {/* DR-FSV-4: Zero-issues success state */}
                            {totalIssueCount(unifiedResults) === 0 && (
                                <SuccessBanner categories={ranCategories(unifiedResults)} />
                            )}

                            {/* Quality Score Card */}
                            {unifiedResults.quality && (
                                <Card className={scoreBg(unifiedResults.quality.score)}>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">Quality Score</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex items-baseline gap-3 mb-3">
                                            <span
                                                className={`text-3xl font-bold ${scoreColor(unifiedResults.quality.score)}`}
                                            >
                                                {(unifiedResults.quality.score * 100).toFixed(0)}%
                                            </span>
                                            <span className="text-sm text-gray-500">
                                                ({unifiedResults.quality.score.toFixed(2)})
                                            </span>
                                        </div>
                                        {unifiedResults.quality.flags.length > 0 ? (
                                            <ul className="space-y-1">
                                                {unifiedResults.quality.flags.map((flag, i) => (
                                                    <li key={i} className="text-sm flex items-start gap-2">
                                                        <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                                                        {flag}
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-green-700">No quality flags raised.</p>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Plain Language Card */}
                            {unifiedResults.plainLanguage && (
                                <Card>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">Plain Language</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 gap-4 mb-3">
                                            <div>
                                                <p className="text-xs text-gray-500 uppercase tracking-wide">
                                                    Flesch Score
                                                </p>
                                                <p className="text-xl font-semibold">
                                                    {unifiedResults.plainLanguage.flesch_score.toFixed(1)}
                                                </p>
                                            </div>
                                            <div>
                                                <p className="text-xs text-gray-500 uppercase tracking-wide">
                                                    Grade Level
                                                </p>
                                                <p className="text-xl font-semibold">
                                                    {unifiedResults.plainLanguage.grade_level.toFixed(1)}
                                                </p>
                                            </div>
                                        </div>
                                        {unifiedResults.plainLanguage.recommendation && (
                                            <p className="text-sm text-gray-700 bg-gray-50 rounded p-2">
                                                {unifiedResults.plainLanguage.recommendation}
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* DR-FSV-3/5/6: Collapsible Acronym Issues */}
                            <CollapsibleSection
                                title="Acronym Issues"
                                count={unifiedResults.acronyms.length}
                                defaultOpen={unifiedResults.acronyms.length > 0}
                            >
                                <Card>
                                    <CardContent className="pt-4">
                                        {unifiedResults.acronyms.length > 0 ? (
                                            <ul className="space-y-2">
                                                {unifiedResults.acronyms.map((a, i) => (
                                                    <li
                                                        key={i}
                                                        className="rounded-lg border border-gray-100 bg-white p-3 space-y-1.5"
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <SeverityBadge severity="warning" />
                                                            <span className="text-xs text-gray-400 font-mono">
                                                                FAA Order 1320.46D §4.2
                                                            </span>
                                                        </div>
                                                        <p className="text-sm text-gray-800">
                                                            Undefined acronym:{" "}
                                                            <strong>{a.acronym}</strong>
                                                            {a.location ? ` — ${a.location}` : ""}
                                                        </p>
                                                        <HowToFix text="Define the acronym on first use, e.g. 'Federal Aviation Administration (FAA)'." />
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-green-700">
                                                No undefined acronyms found.
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            </CollapsibleSection>

                            {/* DR-FSV-3/5/6: Collapsible Style Issues */}
                            <CollapsibleSection
                                title="Style Issues"
                                count={unifiedResults.styleIssues.length}
                                defaultOpen={unifiedResults.styleIssues.length > 0}
                            >
                                <Card>
                                    <CardContent className="pt-4">
                                        {unifiedResults.styleIssues.length > 0 ? (
                                            <ul className="space-y-2">
                                                {unifiedResults.styleIssues.map((s, i) => (
                                                    <li
                                                        key={i}
                                                        className="rounded-lg border border-gray-100 bg-white p-3 space-y-1.5"
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <SeverityBadge severity="error" />
                                                            <span className="text-xs text-gray-400 font-mono">
                                                                AP Style Guide
                                                            </span>
                                                        </div>
                                                        <p className="text-sm text-gray-800">{s.issue}</p>
                                                        {s.suggestion && (
                                                            <HowToFix text={s.suggestion} />
                                                        )}
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-green-700">
                                                No style issues detected.
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            </CollapsibleSection>

                            {/* Regulatory Citations Card */}
                            {unifiedResults.regulatory && (
                                <Card>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">Regulatory Citations</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        {unifiedResults.regulatory.summary && (
                                            <p className="text-sm text-gray-700 mb-3">
                                                {unifiedResults.regulatory.summary}
                                            </p>
                                        )}
                                        {unifiedResults.regulatory.citations.length > 0 ? (
                                            <ul className="space-y-2">
                                                {unifiedResults.regulatory.citations.map((c, i) => (
                                                    <li
                                                        key={i}
                                                        className="text-sm flex items-start gap-2"
                                                    >
                                                        {c.status === "valid" ||
                                                        c.status === "pass" ? (
                                                            <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                                                        ) : (
                                                            <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                                                        )}
                                                        <span>
                                                            <strong>{c.citation}</strong>
                                                            {" — "}
                                                            {c.status}
                                                            {c.detail ? `: ${c.detail}` : ""}
                                                        </span>
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-gray-500">
                                                No regulatory citations found in document.
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* DR-FSV-3/5/6: Collapsible Heading Issues */}
                            <CollapsibleSection
                                title="Heading Structure"
                                count={unifiedResults.headings.length}
                                defaultOpen={unifiedResults.headings.length > 0}
                            >
                                <Card>
                                    <CardContent className="pt-4">
                                        {unifiedResults.headings.length > 0 ? (
                                            <ul className="space-y-2">
                                                {unifiedResults.headings.map((h, i) => (
                                                    <li
                                                        key={i}
                                                        className="rounded-lg border border-gray-100 bg-white p-3 space-y-1.5"
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <SeverityBadge severity="warning" />
                                                            <span className="text-xs text-gray-400 font-mono">
                                                                FAA Order 1320.46D §3
                                                            </span>
                                                        </div>
                                                        <p className="text-sm font-medium text-gray-800">
                                                            {h.heading}
                                                        </p>
                                                        <p className="text-sm text-gray-600">{h.issue}</p>
                                                        <HowToFix text="Ensure headings follow the document hierarchy (H1 > H2 > H3) without skipping levels." />
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-green-700">
                                                No heading structure issues found.
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            </CollapsibleSection>
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}

/* ---------- Coming Soon Panel ---------- */

function AdditionalEnginesPanel() {
    const futureEngines = [
        {
            name: "Grammarly",
            description:
                "AI-powered writing assistance with advanced grammar, tone, and clarity suggestions.",
        },
        {
            name: "Acrolinx",
            description:
                "Enterprise-grade content governance for terminology consistency and brand compliance.",
        },
        {
            name: "Open-source grammar engine",
            description:
                "Community-maintained grammar engine (e.g., LanguageTool) integrated as a peer validation pass.",
        },
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3">
                <Clock className="h-5 w-5 text-amber-600 shrink-0" />
                <p className="text-sm text-amber-800">
                    Additional validation engines are planned. Enable a second checker via the
                    Plugin Marketplace once installed.
                </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {futureEngines.map((engine) => (
                    <Card key={engine.name} className="opacity-60">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Clock className="h-4 w-4 text-gray-400" />
                                {engine.name}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-sm text-gray-500">{engine.description}</p>
                            <span className="mt-3 inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                                Coming Soon
                            </span>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}

/* ---------- Page ---------- */

export default function DocumentQualityPage() {
    return (
        <div className="p-8 space-y-8 max-w-4xl mx-auto">
            {/* Page header */}
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold">Document Quality Checker</h1>
                    <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                        Powered by Federal Style Validator
                    </span>
                </div>
                <p className="text-gray-500 text-sm">
                    Validate documents against federal style guidelines (FAA/DoD), plain language
                    standards, acronym compliance, and regulatory requirements. Additional
                    validation engines can be configured below.
                </p>
            </div>

            {/* Engine tabs */}
            <Tabs defaultValue="fsv">
                <TabsList>
                    <TabsTrigger value="fsv">
                        <span className="flex items-center gap-2">
                            <Shield className="h-4 w-4" />
                            Federal Style Validator
                        </span>
                    </TabsTrigger>
                    <TabsTrigger value="additional">
                        <span className="flex items-center gap-2">
                            <Clock className="h-4 w-4" />
                            Additional Engines
                        </span>
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="fsv" className="mt-6">
                    <FederalStyleValidatorPanel />
                </TabsContent>

                <TabsContent value="additional" className="mt-6">
                    <AdditionalEnginesPanel />
                </TabsContent>
            </Tabs>
        </div>
    );
}
