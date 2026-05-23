"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { authenticatedFetch } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Finding {
  id?: string;
  category?: string;
  severity?: string;
  message?: string;
  location?: Record<string, unknown> | null;
}

interface DocumentQualityResult {
  result_id: string | null;
  total_issues: number;
  issue_count_by_severity: Record<string, number>;
  has_errors: boolean;
  findings: Finding[];
  document: { path?: string; type?: string };
  metadata: Record<string, unknown>;
  fun_facts: unknown[];
  source: string;
}

interface UsageMetrics {
  total_requests: number;
  processed: number;
  failed: number;
  by_doc_type: Record<string, number>;
  by_severity: Record<string, number>;
  window_started_at: string;
  window_ended_at: string;
}

interface ReportItem {
  result_id: string;
  created_at: string;
  doc_type: string | null;
  has_errors: boolean | null;
  severity: string | null;
  filename: string | null;
}

type ActiveView = "validator" | "styleguide" | "rulesreference" | "metrics";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DOC_TYPES = ["Default", "Advisory Circular", "Order"];

const VISIBILITY_CATEGORIES = [
  { key: "readability", label: "Readability", description: "Sentence complexity and reading level" },
  { key: "analysis", label: "Analysis", description: "Style analysis and quality metrics" },
  { key: "paragraph_length", label: "Paragraph Length", description: "Long paragraph checks" },
  { key: "terminology", label: "Terminology", description: "Preferred and prohibited wording" },
  { key: "acronym", label: "Acronyms", description: "Undefined or overused acronyms" },
  { key: "headings", label: "Headings", description: "Heading hierarchy and numbering" },
  { key: "structure", label: "Structure", description: "Section order and document flow" },
  { key: "format", label: "Format", description: "Lists, spacing, dates, and layout" },
  { key: "accessibility", label: "Accessibility", description: "Alt text and accessibility checks" },
  { key: "document_status", label: "Document Status", description: "Draft and final status markers" },
];

const SEVERITY_LEVELS = [
  { key: "error", label: "Errors", description: "Must-fix issues" },
  { key: "warning", label: "Warnings", description: "Should-fix issues" },
  { key: "info", label: "Info", description: "Suggestions and low-risk notes" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function normalizeExternalUrl(value: string | undefined): string | null {
  const trimmed = (value || "").trim();
  if (!trimmed) return null;
  try {
    const url = new URL(trimmed);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

export function resolveFsvFrontendUrl(): string | null {
  return normalizeExternalUrl(process.env.NEXT_PUBLIC_FSV_FRONTEND_URL);
}

function normalizeSeverity(value: string | undefined): "error" | "warning" | "info" {
  const v = (value || "info").toLowerCase();
  if (v === "error" || v === "warning") return v;
  return "info";
}

function formatCategory(value: string | undefined): string {
  return (value || "general").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatLocation(location: Record<string, unknown> | null | undefined): string {
  if (!location) return "";
  for (const key of ["heading", "paragraph", "section", "line", "path"]) {
    const v = location[key];
    if (v !== undefined && v !== null && String(v).trim() !== "") {
      return key === "line" ? `Line ${v}` : String(v);
    }
  }
  return "";
}

function severityColor(sev: string): string {
  if (sev === "error") return "bg-red-50 text-red-700";
  if (sev === "warning") return "bg-amber-50 text-amber-700";
  return "bg-blue-50 text-blue-700";
}

function severityPillColor(sev: string): string {
  if (sev === "error") return "bg-red-100 text-red-700";
  if (sev === "warning") return "bg-amber-100 text-amber-700";
  return "bg-blue-100 text-blue-700";
}

// Minimal markdown-to-HTML renderer (headings, tables, bold, code, bullets)
function markdownToHtml(md: string): string {
  const lines = md.split("\n");
  const out: string[] = [];
  let inTable = false;
  let tableRowIndex = 0;

  const esc = (s: string) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const inline = (s: string) =>
    esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");

  for (const line of lines) {
    if (inTable && line.trim() === "") {
      out.push("</tbody></table>"); inTable = false; tableRowIndex = 0;
      out.push("<p></p>"); continue;
    }
    if (line.trim().startsWith("|")) {
      const cells = line.split("|").slice(1, -1).map((c) => c.trim());
      if (cells.every((c) => /^[-:]+$/.test(c))) { tableRowIndex++; continue; }
      if (!inTable) {
        out.push('<table class="dq-table"><thead>'); inTable = true; tableRowIndex = 0;
      }
      if (tableRowIndex === 0) {
        out.push("<tr>" + cells.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr>");
        out.push("</thead><tbody>");
      } else {
        out.push("<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>");
      }
      tableRowIndex++; continue;
    }
    if (inTable) { out.push("</tbody></table>"); inTable = false; tableRowIndex = 0; }
    const hm = line.match(/^(#{1,4})\s+(.+)$/);
    if (hm) { out.push(`<h${hm[1].length} class="dq-h${hm[1].length}">${inline(hm[2])}</h${hm[1].length}>`); continue; }
    if (/^---+$/.test(line.trim())) { out.push("<hr class='dq-hr' />"); continue; }
    const bm = line.match(/^[-*]\s+(.+)$/);
    if (bm) { out.push(`<li class="dq-li">${inline(bm[1])}</li>`); continue; }
    if (line.trim() === "" || line.trim().startsWith("<!--")) { out.push("<p></p>"); continue; }
    out.push(`<p class="dq-p">${inline(line)}</p>`);
  }
  if (inTable) out.push("</tbody></table>");
  return out.join("\n");
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function UploadPanel({
  file, setFile, docType, setDocType,
}: {
  file: File | null;
  setFile: (f: File | null) => void;
  docType: string;
  setDocType: (v: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  const openPicker = () => inputRef.current?.click();

  return (
    <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">Source document</h2>
          <p className="text-sm text-slate-500 mt-0.5">Upload one Word file to validate.</p>
        </div>
        {file && (
          <button
            type="button"
            className="text-sm font-bold text-blue-600 hover:text-blue-700"
            onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = ""; }}
          >
            Clear
          </button>
        )}
      </div>

      <div
        role="button"
        tabIndex={0}
        className={[
          "flex justify-between items-center gap-3 border-dashed border-2 rounded-xl p-3 cursor-pointer transition-all",
          dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/50",
          file ? "border-solid border-green-300 bg-green-50/50" : "",
        ].join(" ")}
        onClick={openPicker}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragging(false);
          setFile(e.dataTransfer.files?.[0] ?? null);
        }}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openPicker(); } }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".docx"
          className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-label="Upload DOCX file"
        />
        <div className="min-w-0">
          {file ? (
            <>
              <span className="inline-flex text-xs font-bold bg-green-100 text-green-700 rounded-full px-2 py-0.5 mb-1">Ready</span>
              <p className="text-sm font-bold text-slate-900 truncate">{file.name}</p>
              <p className="text-xs text-slate-500">{(file.size / 1048576).toFixed(2)} MB</p>
            </>
          ) : (
            <>
              <span className="inline-flex text-xs font-bold bg-white text-blue-600 rounded-full px-2 py-0.5 mb-1 border border-slate-200">Drop a .docx or browse</span>
              <p className="text-sm font-bold text-slate-900">Upload a DOCX document</p>
              <p className="text-xs text-slate-500">One file at a time.</p>
            </>
          )}
        </div>
        <button
          type="button"
          className="shrink-0 border border-slate-200 rounded-full bg-white text-slate-700 text-sm font-semibold px-3 py-1.5 hover:bg-slate-50"
          onClick={(e) => { e.stopPropagation(); openPicker(); }}
        >
          Browse
        </button>
      </div>

      <label className="block text-sm font-bold text-slate-900 mt-3 mb-1.5" htmlFor="dq-doc-type">
        Document type
      </label>
      <select
        id="dq-doc-type"
        value={docType}
        onChange={(e) => setDocType(e.target.value)}
        className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 text-sm px-3 py-2.5"
      >
        {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
      </select>
    </section>
  );
}

function CollapseToggle({
  title, summary, open, onToggle, children,
}: {
  title: string; summary: string; open: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
      <button
        type="button"
        className="w-full flex justify-between items-center text-left"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span>
          <span className="block text-base font-bold text-slate-900">{title}</span>
          <span className="block text-sm text-slate-500 mt-0.5">{summary}</span>
        </span>
        <span className="text-sm font-bold text-blue-600 shrink-0 ml-3">{open ? "Hide" : "Show"}</span>
      </button>
      {open && <div className="mt-3">{children}</div>}
    </section>
  );
}

function CheckboxRow({
  label, description, checked, onChange,
}: {
  label: string; description: string; checked: boolean; onChange: () => void;
}) {
  return (
    <label className="grid grid-cols-[auto_1fr] gap-3 items-start bg-slate-50 rounded-xl px-3 py-2.5 cursor-pointer">
      <input type="checkbox" checked={checked} onChange={onChange} className="mt-0.5" />
      <span>
        <span className="block text-sm font-bold text-slate-900">{label}</span>
        <span className="block text-xs text-slate-500 mt-0.5">{description}</span>
      </span>
    </label>
  );
}

function VisibilityToggles({
  visibility, setVisibility,
}: {
  visibility: Record<string, boolean>;
  setVisibility: (v: Record<string, boolean>) => void;
}) {
  const [open, setOpen] = useState(false);
  const hidden = VISIBILITY_CATEGORIES.filter((c) => !visibility[c.key]).length;

  return (
    <CollapseToggle
      title="Category visibility"
      summary={hidden === 0 ? "All categories enabled" : `${hidden} hidden`}
      open={open}
      onToggle={() => setOpen((p) => !p)}
    >
      <div className="flex gap-2 mb-2.5">
        <button
          type="button"
          className="border border-slate-200 rounded-full bg-white text-slate-700 text-xs font-semibold px-3 py-1 hover:bg-slate-50"
          onClick={() => setVisibility(Object.fromEntries(VISIBILITY_CATEGORIES.map((c) => [c.key, true])))}
        >
          Show all
        </button>
        <button
          type="button"
          className="border border-slate-200 rounded-full bg-white text-slate-700 text-xs font-semibold px-3 py-1 hover:bg-slate-50"
          onClick={() => setVisibility(Object.fromEntries(VISIBILITY_CATEGORIES.map((c) => [c.key, false])))}
        >
          Hide all
        </button>
      </div>
      <div className="grid gap-1.5" role="group" aria-label="Category visibility">
        {VISIBILITY_CATEGORIES.map((c) => (
          <CheckboxRow
            key={c.key}
            label={c.label}
            description={c.description}
            checked={visibility[c.key]}
            onChange={() => setVisibility({ ...visibility, [c.key]: !visibility[c.key] })}
          />
        ))}
      </div>
    </CollapseToggle>
  );
}

function SeverityToggles({
  severity, setSeverity,
}: {
  severity: Record<string, boolean>;
  setSeverity: (v: Record<string, boolean>) => void;
}) {
  const [open, setOpen] = useState(false);
  const hidden = SEVERITY_LEVELS.filter((s) => !severity[s.key]).length;

  return (
    <CollapseToggle
      title="Severity filters"
      summary={hidden === 0 ? "All severities visible" : `${hidden} hidden`}
      open={open}
      onToggle={() => setOpen((p) => !p)}
    >
      <div className="flex gap-2 mb-2.5">
        <button type="button" className="border border-slate-200 rounded-full bg-white text-slate-700 text-xs font-semibold px-3 py-1" onClick={() => setSeverity({ error: true, warning: true, info: true })}>All</button>
        <button type="button" className="border border-slate-200 rounded-full bg-white text-slate-700 text-xs font-semibold px-3 py-1" onClick={() => setSeverity({ error: true, warning: false, info: false })}>Errors only</button>
        <button type="button" className="border border-slate-200 rounded-full bg-white text-slate-700 text-xs font-semibold px-3 py-1" onClick={() => setSeverity({ error: true, warning: true, info: false })}>Hide info</button>
      </div>
      <div className="grid gap-1.5" role="group" aria-label="Severity filters">
        {SEVERITY_LEVELS.map((s) => (
          <CheckboxRow
            key={s.key}
            label={s.label}
            description={s.description}
            checked={severity[s.key]}
            onChange={() => setSeverity({ ...severity, [s.key]: !severity[s.key] })}
          />
        ))}
      </div>
    </CollapseToggle>
  );
}

function ResultsPane({
  result, severityFilters,
}: {
  result: DocumentQualityResult | null;
  severityFilters: Record<string, boolean>;
}) {
  if (!result) {
    return (
      <div className="border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50 p-8 text-center">
        <p className="text-base font-bold text-slate-900 mb-1">No document processed yet</p>
        <p className="text-sm text-slate-500">Upload a DOCX, configure filters on the left, and click <strong>Run validation</strong>.</p>
      </div>
    );
  }

  const findings = Array.isArray(result.findings) ? result.findings : [];

  // Group + filter
  const grouped = new Map<string, Finding[]>();
  for (const f of findings) {
    const sev = normalizeSeverity(f.severity);
    if (!severityFilters[sev]) continue;
    const cat = f.category || "general";
    grouped.set(cat, [...(grouped.get(cat) || []), f]);
  }
  const groups = [...grouped.entries()]
    .map(([cat, items]) => ({ cat, items: items.sort((a, b) => { const o = { error: 0, warning: 1, info: 2 }; return o[normalizeSeverity(a.severity)] - o[normalizeSeverity(b.severity)]; }) }))
    .sort((a, b) => {
      const ae = a.items.some((f) => normalizeSeverity(f.severity) === "error");
      const be = b.items.some((f) => normalizeSeverity(f.severity) === "error");
      if (ae !== be) return ae ? -1 : 1;
      return a.cat.localeCompare(b.cat);
    });

  const metaEntries = Object.entries(result.metadata || {}).filter(([, v]) => v);
  const funFacts = Array.isArray(result.fun_facts)
    ? result.fun_facts.map((f) => String(f)).filter((f) => f.trim())
    : [];

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-3 bg-slate-50 rounded-xl p-3">
        <div>
          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wide">Document</span>
          <span className="block text-sm font-semibold text-slate-900 mt-0.5 break-words">{result.document?.path || "Current upload"}</span>
        </div>
        <div>
          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wide">Type</span>
          <span className="block text-sm font-semibold text-slate-900 mt-0.5">{result.document?.type || "Not set"}</span>
        </div>
      </div>

      {groups.length === 0 ? (
        <div className="border border-slate-200 rounded-xl bg-slate-50 p-4 text-sm font-semibold text-slate-500">
          No findings match the current severity filters.
        </div>
      ) : (
        <div className="grid gap-2">
          {groups.map(({ cat, items }) => {
            const ec = items.filter((f) => normalizeSeverity(f.severity) === "error").length;
            const wc = items.filter((f) => normalizeSeverity(f.severity) === "warning").length;
            const ic = items.filter((f) => normalizeSeverity(f.severity) === "info").length;
            return (
              <details key={cat} className="border border-slate-200 rounded-xl bg-white overflow-hidden" open={ec > 0}>
                <summary className="flex justify-between items-center px-4 py-3 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                  <span className="text-sm font-bold text-slate-900">{formatCategory(cat)} ({items.length})</span>
                  <span className="flex gap-1.5 flex-wrap">
                    {ec > 0 && <span className="inline-flex text-xs font-bold bg-red-100 text-red-700 rounded-full px-2 py-0.5">E {ec}</span>}
                    {wc > 0 && <span className="inline-flex text-xs font-bold bg-amber-100 text-amber-700 rounded-full px-2 py-0.5">W {wc}</span>}
                    {ic > 0 && <span className="inline-flex text-xs font-bold bg-blue-100 text-blue-700 rounded-full px-2 py-0.5">I {ic}</span>}
                  </span>
                </summary>
                <div className="px-4 pb-3">
                  {items.map((f, i) => {
                    const sev = normalizeSeverity(f.severity);
                    const loc = formatLocation(f.location);
                    return (
                      <article key={`${cat}-${f.id || i}`} className="grid grid-cols-[auto_1fr] gap-3 items-start py-3 border-t border-slate-100 first:border-t-0">
                        <span className={`inline-flex text-xs font-bold rounded-full px-2 py-0.5 capitalize ${severityColor(sev)}`}>{sev}</span>
                        <div>
                          <p className="text-sm font-semibold text-slate-900 m-0">{f.message || "Finding"}</p>
                          <div className="flex gap-2 flex-wrap mt-1">
                            {f.id && <span className="text-xs font-bold text-slate-500">{f.id}</span>}
                            {loc && <span className="text-xs text-slate-400">{loc}</span>}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </details>
            );
          })}
        </div>
      )}

      {metaEntries.length > 0 && (
        <details className="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <summary className="flex justify-between items-center px-4 py-3 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
            <span className="text-sm font-bold text-slate-900">Document metadata</span>
          </summary>
          <div className="px-4 pb-3 grid gap-2">
            {metaEntries.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[160px_1fr] gap-3">
                <span className="text-sm text-slate-500">{formatCategory(k)}</span>
                <span className="text-sm font-semibold text-slate-900 break-words">{String(v)}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      {funFacts.length > 0 && (
        <details className="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <summary className="flex justify-between items-center px-4 py-3 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
            <span className="text-sm font-bold text-slate-900">Writing notes</span>
          </summary>
          <ul className="px-4 pb-3 pl-8 list-disc text-sm text-slate-900 space-y-1">
            {funFacts.map((f) => <li key={f}>{f}</li>)}
          </ul>
        </details>
      )}
    </div>
  );
}

function ReferenceTab({ endpoint, title, subtitle }: { endpoint: string; title: string; subtitle: string }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true); setError(null);
    authenticatedFetch(endpoint)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: { content: string }) => { if (active) { setContent(d.content); setLoading(false); } })
      .catch((e: unknown) => { if (active) { setError(String(e)); setLoading(false); } });
    return () => { active = false; };
  }, [endpoint]);

  const html = content ? markdownToHtml(content) : "";
  const highlighted = search.trim().length > 1
    ? html.replace(new RegExp(`(${search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"), '<mark style="background:#fef08a">$1</mark>')
    : html;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
      <div className="flex justify-between items-start gap-4 mb-5">
        <div>
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>
          <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
        </div>
        <input
          type="search"
          className="border border-slate-200 rounded-xl bg-slate-50 text-sm px-3 py-2 w-56 shrink-0"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label={`Search ${title}`}
        />
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-slate-500 py-8">
          <div className="w-5 h-5 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin" />
          <span>Loading…</span>
        </div>
      )}
      {error && <p className="text-sm text-red-600 py-4">Failed to load: {error}</p>}
      {!loading && !error && (
        <div
          className="prose prose-slate prose-sm max-w-none [&_.dq-table]:w-full [&_.dq-table]:border-collapse [&_.dq-table_th]:border [&_.dq-table_th]:border-slate-200 [&_.dq-table_th]:bg-slate-50 [&_.dq-table_th]:px-3 [&_.dq-table_th]:py-2 [&_.dq-table_td]:border [&_.dq-table_td]:border-slate-200 [&_.dq-table_td]:px-3 [&_.dq-table_td]:py-2 [&_.dq-h1]:text-2xl [&_.dq-h1]:font-bold [&_.dq-h2]:text-xl [&_.dq-h2]:font-bold [&_.dq-h3]:text-base [&_.dq-h3]:font-bold [&_.dq-h4]:text-sm [&_.dq-h4]:font-bold [&_.dq-li]:ml-4 [&_.dq-li]:list-disc [&_.dq-hr]:border-slate-200 [&_.dq-p]:text-slate-700"
          dangerouslySetInnerHTML={{ __html: highlighted }}
        />
      )}
    </div>
  );
}

function MetricsTab() {
  const [usage, setUsage] = useState<UsageMetrics | null>(null);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [ur, rr] = await Promise.all([
        authenticatedFetch("/tools/document-quality/usage"),
        authenticatedFetch("/tools/document-quality/reports"),
      ]);
      if (!ur.ok || !rr.ok) throw new Error("Failed to load metrics");
      const [u, r] = await Promise.all([ur.json(), rr.json()]) as [UsageMetrics, ReportItem[]];
      setUsage(u); setReports(r);
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const docTypeEntries = usage ? Object.entries(usage.by_doc_type).sort(([, a], [, b]) => b - a) : [];
  const maxDT = docTypeEntries.reduce((m, [, v]) => Math.max(m, v), 1);
  const sevEntries = usage ? Object.entries(usage.by_severity) : [];
  const sevTotal = sevEntries.reduce((s, [, v]) => s + v, 0);
  const sevColors: Record<string, string> = { error: "bg-red-500", warning: "bg-amber-500", info: "bg-blue-500", critical: "bg-orange-500", high: "bg-red-600", medium: "bg-amber-400", low: "bg-blue-400" };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-bold text-slate-900">Metrics dashboard</h2>
        <button
          type="button"
          className="border border-slate-200 rounded-full bg-white text-slate-700 text-sm font-semibold px-4 py-1.5 hover:bg-slate-50"
          onClick={fetchAll}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
          <h3 className="text-sm font-bold text-slate-900 mb-3">Request volume</h3>
          {usage?.window_started_at && (
            <p className="text-xs text-slate-500 mb-2">{usage.window_started_at} → {usage.window_ended_at}</p>
          )}
          <div className="space-y-2">
            {[["Total requests", usage?.total_requests ?? 0], ["Processed", usage?.processed ?? 0], ["Failed", usage?.failed ?? 0]].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between text-sm">
                <span className="text-slate-500">{String(k)}</span>
                <strong className="text-slate-900">{String(v)}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
          <h3 className="text-sm font-bold text-slate-900 mb-3">By document type</h3>
          {docTypeEntries.length > 0 ? (
            <div className="space-y-2">
              {docTypeEntries.map(([dt, count]) => (
                <div key={dt} className="flex items-center gap-2">
                  <span className="text-sm text-slate-600 w-28 truncate">{dt}</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.round((count / maxDT) * 100)}%` }} />
                  </div>
                  <span className="text-sm text-slate-900 w-6 text-right">{count}</span>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-slate-500">No data yet.</p>}
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
          <h3 className="text-sm font-bold text-slate-900 mb-3">By severity</h3>
          {sevEntries.length > 0 ? (
            <div className="space-y-2">
              {sevTotal > 0 && (
                <div className="flex h-3 rounded-full overflow-hidden bg-slate-100 mb-3">
                  {sevEntries.filter(([, v]) => v > 0).map(([sev, count]) => (
                    <div key={sev} className={`${sevColors[sev.toLowerCase()] || "bg-slate-400"}`} style={{ flexGrow: count }} title={`${sev}: ${count}`} />
                  ))}
                </div>
              )}
              {sevEntries.map(([sev, count]) => (
                <div key={sev} className="flex justify-between text-sm">
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <span className={`w-2.5 h-2.5 rounded-full ${sevColors[sev.toLowerCase()] || "bg-slate-400"}`} />
                    {sev}
                  </span>
                  <strong className="text-slate-900">{count} · {sevTotal ? Math.round((count / sevTotal) * 100) : 0}%</strong>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-slate-500">No data yet.</p>}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-bold text-slate-900">Latest reports</h3>
          <span className="text-xs font-bold bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">{reports.length} reports</span>
        </div>
        {reports.length === 0 ? (
          <p className="text-sm text-slate-500">No reports yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-bold text-slate-500 uppercase border-b border-slate-100">
                  <th className="pb-2 pr-4">Result ID</th>
                  <th className="pb-2 pr-4">Document</th>
                  <th className="pb-2 pr-4">Severity</th>
                  <th className="pb-2 pr-4">Errors</th>
                  <th className="pb-2">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {reports.map((r) => (
                  <tr key={r.result_id}>
                    <td className="py-2 pr-4 font-mono text-slate-600">{r.result_id.slice(0, 10)}…</td>
                    <td className="py-2 pr-4 text-slate-700">{r.doc_type || r.filename || "Unknown"}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-flex text-xs font-bold rounded-full px-2 py-0.5 ${severityPillColor(r.severity || "")}`}>{r.severity || "n/a"}</span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block w-2.5 h-2.5 rounded-full ${r.has_errors === null ? "bg-slate-300" : r.has_errors ? "bg-red-500" : "bg-green-500"}`} aria-label={r.has_errors === null ? "n/a" : r.has_errors ? "Yes" : "No"} />
                    </td>
                    <td className="py-2 text-slate-500 text-xs">{r.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DocumentQualityPage() {
  const [activeView, setActiveView] = useState<ActiveView>("validator");
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState("Default");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DocumentQualityResult | null>(null);

  const [visibility, setVisibility] = useState<Record<string, boolean>>(
    Object.fromEntries(VISIBILITY_CATEGORIES.map((c) => [c.key, true])),
  );
  const [severity, setSeverity] = useState<Record<string, boolean>>({
    error: true, warning: true, info: true,
  });

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true); setError(null);

    const form = new FormData();
    form.append("doc_file", file);
    form.append("doc_type", docType);
    form.append("visibility_json", JSON.stringify(visibility));
    form.append("group_by", "category");

    try {
      const res = await authenticatedFetch("/tools/document-quality", { method: "POST", body: form });
      if (!res.ok) {
        const detail = await res.json().then((d: { detail?: string }) => d.detail).catch(() => null);
        throw new Error(detail || `Error ${res.status}`);
      }
      const data = await res.json() as DocumentQualityResult;
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "An unexpected error occurred");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const hasResults = Boolean(result);
  const statusTone = !hasResults ? "idle" : result?.has_errors ? "fail" : "pass";
  const statusLabel = !hasResults ? "Awaiting" : result?.has_errors ? "Needs review" : "Clear";
  const statusClasses = {
    idle: "bg-slate-100 text-slate-500",
    pass: "bg-green-100 text-green-700",
    fail: "bg-red-100 text-red-700",
  }[statusTone];
  const dotClasses = {
    idle: "bg-slate-400",
    pass: "bg-green-600",
    fail: "bg-red-600",
  }[statusTone];

  const tabs: { key: ActiveView; label: string }[] = [
    { key: "validator", label: "Validator" },
    { key: "styleguide", label: "Style Guide" },
    { key: "rulesreference", label: "Rules Reference" },
    { key: "metrics", label: "Metrics" },
  ];

  const fsvFrontendUrl = resolveFsvFrontendUrl();
  const [showEmbeddedFsv, setShowEmbeddedFsv] = useState(Boolean(fsvFrontendUrl));

  if (fsvFrontendUrl && showEmbeddedFsv) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50/60 via-slate-50 to-slate-100">
        <div className="max-w-screen-xl mx-auto px-5 py-8 pb-12">
          <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-blue-600 mb-1">
                  Document Validation
                </p>
                <h1 className="text-2xl font-bold text-slate-900">Federal Style Validator</h1>
                <p className="mt-1 max-w-2xl text-sm text-slate-500">
                  Showing the configured standalone FSV frontend. If the embedded app is blank
                  or unavailable, continue with the built-in validator.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <a
                  href={fsvFrontendUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                >
                  Open standalone
                </a>
                <button
                  type="button"
                  className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700"
                  onClick={() => setShowEmbeddedFsv(false)}
                >
                  Use built-in validator
                </button>
              </div>
            </div>
          </div>
          <iframe
            src={fsvFrontendUrl}
            className="w-full border-0 rounded-xl"
            style={{ height: "calc(100vh - 6rem)" }}
            title="Federal Style Validator"
            allowFullScreen
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50/60 via-slate-50 to-slate-100">
      <div className="max-w-screen-xl mx-auto px-5 py-8 pb-12">

        {/* Header */}
        <header className="flex flex-wrap justify-between items-start gap-4 mb-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-blue-600 mb-1">Document Validation</p>
            <h1 className="text-3xl font-bold text-slate-900">Federal Style Validator</h1>
            <p className="text-sm text-slate-500 mt-2 max-w-2xl">
              Analyzes documents against federal writing standards to identify clarity, consistency,
              and compliance issues, and provides actionable recommendations.
            </p>
          </div>
          <div className="inline-flex flex-wrap gap-1.5 p-1.5 border border-slate-200 rounded-full bg-white/80 shadow-sm" role="tablist" aria-label="Views">
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={activeView === t.key}
                className={[
                  "rounded-full text-sm font-semibold px-4 py-2 transition-colors",
                  activeView === t.key
                    ? "bg-blue-600 text-white"
                    : "text-slate-500 hover:text-slate-700",
                ].join(" ")}
                onClick={() => setActiveView(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </header>

        {/* Error banner */}
        {error && (
          <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4">
            <span className="text-red-600 text-sm flex-1">{error}</span>
            <button type="button" className="text-red-400 hover:text-red-600 text-lg leading-none" onClick={() => setError(null)} aria-label="Dismiss">×</button>
          </div>
        )}

        {/* Tab content */}
        {activeView === "styleguide" && (
          <ReferenceTab
            endpoint="/tools/document-quality/style-guide"
            title="Style Guide Reference"
            subtitle="Every check category, rule ID, and fix guidance — generated from the active validator configuration."
          />
        )}
        {activeView === "rulesreference" && (
          <ReferenceTab
            endpoint="/tools/document-quality/rules-reference"
            title="Rules Reference"
            subtitle="The canonical rule catalog: stable IDs, descriptions, why they matter, and how to fix them."
          />
        )}
        {activeView === "metrics" && <MetricsTab />}

        {activeView === "validator" && (
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,340px)_1fr] gap-4 items-start">

            {/* Control sidebar */}
            <aside className="grid gap-3 lg:sticky lg:top-4">
              <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4">
                <span className="inline-flex text-xs font-bold bg-blue-50 text-blue-600 rounded-full px-2 py-0.5 mb-2">DOCX only</span>
                <h2 className="text-base font-bold text-slate-900">Controls</h2>
                <p className="text-sm text-slate-500 mt-0.5">Upload a Word document, choose the type, and tune categories.</p>
              </div>

              <UploadPanel file={file} setFile={setFile} docType={docType} setDocType={setDocType} />
              <VisibilityToggles visibility={visibility} setVisibility={setVisibility} />
              <SeverityToggles severity={severity} setSeverity={setSeverity} />

              <button
                type="button"
                className="w-full rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 px-4 shadow-md shadow-blue-200 transition-colors"
                disabled={!file || loading}
                onClick={handleSubmit}
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2 justify-center">
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Validating…
                  </span>
                ) : "Run validation"}
              </button>
            </aside>

            {/* Results panel */}
            <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
              <div className="flex justify-between items-start gap-3 mb-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-blue-600 mb-1">Results</p>
                  <h2 className="text-lg font-bold text-slate-900">Validation findings</h2>
                  <p className="text-sm text-slate-500 mt-0.5">Organized by category.</p>
                </div>
                <span className={`inline-flex items-center gap-1.5 text-sm font-bold rounded-full px-3 py-1.5 shrink-0 ${statusClasses}`}>
                  <span className={`w-2 h-2 rounded-full ${dotClasses}`} />
                  {statusLabel}
                </span>
              </div>

              {/* Summary cards */}
              <div className={`grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 ${!hasResults ? "opacity-60" : ""}`}>
                {[
                  { label: "Total", value: result?.total_issues ?? 0, cls: "text-slate-900" },
                  { label: "Errors", value: result?.issue_count_by_severity?.error ?? 0, cls: "text-red-600" },
                  { label: "Warnings", value: result?.issue_count_by_severity?.warning ?? 0, cls: "text-amber-700" },
                  { label: "Info", value: result?.issue_count_by_severity?.info ?? 0, cls: "text-blue-700" },
                ].map(({ label, value, cls }) => (
                  <div key={label} className="border border-slate-200 rounded-xl bg-slate-50 p-3">
                    <span className="block text-xs font-bold text-slate-500 uppercase tracking-wide">{label}</span>
                    <strong className={`block text-2xl mt-1 leading-none ${cls}`}>{hasResults ? value : "-"}</strong>
                  </div>
                ))}
              </div>

              <ResultsPane result={result} severityFilters={severity} />

              {result?.result_id && (
                <div className="flex gap-3 flex-wrap mt-4 pt-4 border-t border-slate-100">
                  <a
                    href={`/tools/document-quality/results/${result.result_id}.docx`}
                    className="inline-flex items-center border border-slate-200 rounded-xl bg-white text-sm font-bold text-slate-700 px-4 py-2 hover:bg-slate-50"
                    download
                  >
                    Download DOCX
                  </a>
                  <a
                    href={`/tools/document-quality/results/${result.result_id}.pdf`}
                    className="inline-flex items-center border border-slate-200 rounded-xl bg-white text-sm font-bold text-slate-700 px-4 py-2 hover:bg-slate-50"
                    download
                  >
                    Download PDF
                  </a>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
