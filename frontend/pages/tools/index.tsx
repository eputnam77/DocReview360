import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";
import {
    BarChart3,
    FileCheck,
    FileCog,
    Settings,
    SpellCheck,
    Stamp,
    ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

// ---------------------------------------------------------------------------
// Tool catalogue
// ---------------------------------------------------------------------------

type ToolStatus = "active" | "disabled" | "not-installed";

interface ToolItem {
  id: string;
  label: string;
  href: string;
  icon: React.ReactNode;
  desc: string;
  /** true = built-in plugin managed via /plugin-marketplace/builtin-status */
  isBuiltIn: boolean;
  /** true = Core Tool Pack — enabled by default, shown first with Core badge */
  isCore?: boolean;
  /** community / optional plugins that must be installed for this tool */
  requiresPlugins?: string[];
  /** built-in plugins that power this tool */
  includesBuiltIn?: string[];
  /** admin configure link target */
  configHref?: string;
}

const ALL_TOOLS_ITEMS: ToolItem[] = [
  {
    id: "converter",
    label: "Document Converter",
    href: "/tools/converter",
    icon: <FileCog className="w-6 h-6 text-indigo-600" />,
    desc: "Convert Word, Markdown, and TipTap between formats.",
    isBuiltIn: false,
    configHref: "/configuration",
  },
  {
    id: "fedstylevalidator",
    label: "Federal Style Validator",
    href: "/tools/checker",
    icon: <SpellCheck className="w-6 h-6 text-green-600" />,
    desc: "Core tool — validates documents for FAA/DoD style, plain language, acronyms, regulatory references, and readability. Enabled by default for all organizations.",
    isBuiltIn: true,
    isCore: true,
    configHref: "/configuration/document-types",
  },
  {
    id: "scdocbuilder",
    label: "Special Conditions Doc Builder",
    href: "/tools/sc_converter",
    icon: <Stamp className="w-6 h-6 text-rose-600" />,
    desc: "Core tool — generates legally formatted FAA Special Conditions notices with structured template assembly.",
    isBuiltIn: true,
    isCore: true,
    configHref: "/configuration",
  },
  {
    id: "document-analysis",
    label: "Document Analysis",
    href: "/tools/document-analysis",
    icon: <BarChart3 className="w-6 h-6 text-blue-600" />,
    desc: "Analyze readability, sentiment, and extract insights from documents.",
    isBuiltIn: false,
    requiresPlugins: ["textstat", "readability", "textblob", "spacy", "lexnlp"],
    configHref: "/configuration",
  },
  {
    id: "document-quality",
    label: "Document Quality Checker",
    href: "/tools/document-quality",
    icon: <FileCheck className="w-6 h-6 text-emerald-600" />,
    desc: "Check grammar, spelling, style, and accessibility compliance.",
    isBuiltIn: false,
    requiresPlugins: ["language-tool-python", "pyspellchecker", "gingerit"],
    includesBuiltIn: ["fedstylevalidator"],
    configHref: "/configuration",
  },
  {
    id: "document-processor",
    label: "Document Processor",
    href: "/tools/document-processor",
    icon: <Settings className="w-6 h-6 text-purple-600" />,
    desc: "Extract content, convert formats, and compare documents.",
    isBuiltIn: false,
    requiresPlugins: ["pdfplumber", "python-docx", "pypdf", "docling", "mammoth", "textdistance"],
    configHref: "/configuration",
  },
];

// ---------------------------------------------------------------------------
// Status badge component
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: ToolStatus }) {
  if (status === "active") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
        <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
        Active
      </span>
    );
  }
  if (status === "disabled") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400" />
        Disabled
      </span>
    );
  }
  // not-installed
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
      Not installed
    </span>
  );
}

function CommunityBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700">
      Community
    </span>
  );
}

function CoreBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
      <ShieldCheck className="w-3 h-3" />
      Core
    </span>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ToolsPage() {
  const [builtinStatus, setBuiltinStatus] = useState<Record<string, boolean>>({});
  const [installedPlugins, setInstalledPlugins] = useState<Set<string>>(new Set());
  const [communityPlugins, setCommunityPlugins] = useState<Set<string>>(new Set());
  const [toggling, setToggling] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoValidationEnabled, setAutoValidationEnabled] = useState(true);
  const [savingAutoValidation, setSavingAutoValidation] = useState(false);
  const [fsvChecks, setFsvChecks] = useState<Record<string, boolean>>({});
  const [fsvCategories, setFsvCategories] = useState<string[]>([]);
  const [savingFsvCheck, setSavingFsvCheck] = useState<string | null>(null);
  const [fsvUrl, setFsvUrl] = useState("");
  const [fsvUrlInput, setFsvUrlInput] = useState("");
  const [savingFsvUrl, setSavingFsvUrl] = useState(false);

  const isAdmin = useUserStore((s) => s.isAdmin);

  useEffect(() => {
    const load = async () => {
      try {
        // Fetch built-in enable/disable state
        const builtinRes = await authenticatedFetch("/plugin-marketplace/builtin-status");
        if (builtinRes.ok) {
          setBuiltinStatus(await builtinRes.json());
        } else {
          setBuiltinStatus({ fedstylevalidator: true, scdocbuilder: true });
        }

        // Fetch auto-validation setting
        const avRes = await authenticatedFetch("/admin/settings/auto-validation");
        if (avRes.ok) {
          const avData = await avRes.json();
          setAutoValidationEnabled(avData.enabled ?? true);
        }

        // Fetch per-check FSV settings
        const fsvRes = await authenticatedFetch("/admin/settings/fsv-checks");
        if (fsvRes.ok) {
          const fsvData = await fsvRes.json();
          setFsvChecks(fsvData.checks ?? {});
          setFsvCategories(fsvData.categories ?? []);
        }

        // Fetch FSV URL setting
        const fsvUrlRes = await authenticatedFetch("/admin/settings/fsv-url");
        if (fsvUrlRes.ok) {
          const urlData = await fsvUrlRes.json();
          const url = urlData.url ?? "";
          setFsvUrl(url);
          setFsvUrlInput(url);
        }

        // Fetch marketplace plugin list to determine installed + community flags
        const marketRes = await authenticatedFetch("/plugin-marketplace");
        if (marketRes.ok) {
          const plugins: Array<{ id: string; is_community?: boolean; installed?: boolean }> =
            await marketRes.json();
          const installed = new Set<string>();
          const community = new Set<string>();
          for (const p of plugins) {
            if (p.installed) installed.add(p.id);
            if (p.is_community) community.add(p.id);
          }
          setInstalledPlugins(installed);
          setCommunityPlugins(community);
        }
      } catch {
        setBuiltinStatus({ fedstylevalidator: true, scdocbuilder: true });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // Derive per-tool status -------------------------------------------------------

  function getStatus(tool: ToolItem): ToolStatus {
    if (tool.isBuiltIn) {
      return builtinStatus[tool.id] === false ? "disabled" : "active";
    }

    // Non-built-in: active if all required plugins are installed (or no plugins needed)
    const required = tool.requiresPlugins ?? [];
    const builtIns = tool.includesBuiltIn ?? [];

    if (required.length === 0 && builtIns.length === 0) return "active";

    const hasInstalledRequired = required.some((p) => installedPlugins.has(p));
    const hasActiveBuiltIn = builtIns.some((p) => builtinStatus[p] !== false);

    if (hasInstalledRequired || hasActiveBuiltIn) return "active";
    if (required.length > 0) return "not-installed";
    return "disabled";
  }

  function isCommunityTool(tool: ToolItem): boolean {
    if (tool.isBuiltIn) return false;
    const required = tool.requiresPlugins ?? [];
    return required.length > 0 && required.every((p) => communityPlugins.has(p));
  }

  // Toggle auto-validation -------------------------------------------------------

  async function toggleAutoValidation() {
    setSavingAutoValidation(true);
    try {
      const res = await authenticatedFetch("/admin/settings/auto-validation", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !autoValidationEnabled }),
      });
      if (res.ok) {
        setAutoValidationEnabled(!autoValidationEnabled);
        toast.success(`On-save validation ${!autoValidationEnabled ? "enabled" : "disabled"}.`);
      } else {
        toast.error("Failed to update setting.");
      }
    } catch {
      toast.error("Failed to update setting.");
    } finally {
      setSavingAutoValidation(false);
    }
  }

  // Toggle individual FSV check category ------------------------------------------

  async function toggleFsvCheck(category: string) {
    const newVal = !fsvChecks[category];
    setSavingFsvCheck(category);
    try {
      const res = await authenticatedFetch("/admin/settings/fsv-checks", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ checks: { [category]: newVal } }),
      });
      if (res.ok) {
        const data = await res.json();
        setFsvChecks(data.checks ?? { ...fsvChecks, [category]: newVal });
        toast.success(`${formatCheckLabel(category)} ${newVal ? "enabled" : "disabled"}.`);
      } else {
        toast.error("Failed to update check setting.");
      }
    } catch {
      toast.error("Failed to update check setting.");
    } finally {
      setSavingFsvCheck(null);
    }
  }

  function formatCheckLabel(id: string): string {
    return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // Save FSV URL ----------------------------------------------------------------

  async function saveFsvUrl() {
    setSavingFsvUrl(true);
    try {
      const res = await authenticatedFetch("/admin/settings/fsv-url", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: fsvUrlInput || null }),
      });
      if (res.ok) {
        const data = await res.json();
        const saved = data.url ?? "";
        setFsvUrl(saved);
        setFsvUrlInput(saved);
        toast.success(saved ? "FSV URL saved." : "FSV URL cleared.");
      } else {
        toast.error("Failed to save FSV URL.");
      }
    } catch {
      toast.error("Failed to save FSV URL.");
    } finally {
      setSavingFsvUrl(false);
    }
  }

  // Toggle built-in plugin -------------------------------------------------------

  async function togglePlugin(pluginId: string, currentlyEnabled: boolean) {
    setToggling(pluginId);
    try {
      const res = await authenticatedFetch("/plugin-marketplace/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pluginId, enabled: !currentlyEnabled }),
      });
      if (res.ok) {
        setBuiltinStatus((prev) => ({ ...prev, [pluginId]: !currentlyEnabled }));
      }
    } finally {
      setToggling(null);
    }
  }

  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="p-8 space-y-8">
        <h1 className="text-2xl font-bold">Tools</h1>
        <div className="flex items-center justify-center h-32">
          <div className="text-gray-500">Loading tools...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tools</h1>
        {isAdmin && (
          <Link
            href="/plugin-marketplace"
            className="text-sm text-indigo-600 hover:underline"
          >
            Manage plugins
          </Link>
        )}
      </div>

      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
        {ALL_TOOLS_ITEMS.map((tool) => {
          const status = getStatus(tool);
          const isCommunity = isCommunityTool(tool);
          const isDisabled = status === "disabled";
          const isNotInstalled = status === "not-installed";
          const isEnabled = builtinStatus[tool.id] !== false;

          return (
            <div
              key={tool.id}
              className={`group flex flex-col ${isDisabled || isNotInstalled ? "opacity-60" : ""}`}
            >
              <Card
                className={`transition-shadow h-full flex flex-col ${
                  !isDisabled && !isNotInstalled ? "group-hover:shadow-lg" : ""
                }`}
              >
                <CardHeader className="flex flex-row items-start gap-3 pb-2">
                  <div className="mt-0.5">{tool.icon}</div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base font-semibold leading-snug">
                      {tool.label}
                    </CardTitle>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {tool.isCore && <CoreBadge />}
                      <StatusBadge status={status} />
                      {isCommunity && <CommunityBadge />}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="flex-1 flex flex-col justify-between gap-3">
                  <p className="text-sm text-gray-500">{tool.desc}</p>

                  {/* Action row */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Open tool — only when active */}
                    {status === "active" && (
                      <Link
                        href={tool.href}
                        className="inline-block rounded-md bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700"
                      >
                        Open
                      </Link>
                    )}

                    {/* Admin: Toggle built-in on/off */}
                    {isAdmin && tool.isBuiltIn && (
                      <button
                        onClick={() => togglePlugin(tool.id, isEnabled)}
                        disabled={toggling === tool.id}
                        className={`inline-block rounded-md border px-3 py-1 text-xs font-medium transition-colors ${
                          isEnabled
                            ? "border-gray-300 text-gray-600 hover:bg-gray-50"
                            : "border-green-300 text-green-700 hover:bg-green-50"
                        } disabled:opacity-40`}
                      >
                        {toggling === tool.id
                          ? "Saving…"
                          : isEnabled
                          ? "Disable"
                          : "Enable"}
                      </button>
                    )}

                    {/* Admin: Configure link */}
                    {isAdmin && tool.configHref && (
                      <Link
                        href={tool.configHref}
                        className="inline-block rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                      >
                        Configure
                      </Link>
                    )}
                  </div>

                  {/* Not-installed hint */}
                  {isNotInstalled && (
                    <p className="text-xs text-amber-700">
                      Requires optional plugins.{" "}
                      {isAdmin ? (
                        <Link href="/plugin-marketplace" className="underline">
                          Install from marketplace
                        </Link>
                      ) : (
                        "Contact your administrator."
                      )}
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          );
        })}
      </div>

      {ALL_TOOLS_ITEMS.length === 0 && (
        <div className="text-center py-12">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No tools available</h3>
          <p className="text-gray-500">Contact your administrator to enable tools.</p>
        </div>
      )}

      {/* On-save auto-validation — admin panel, shown when FSV is active */}
      {isAdmin && builtinStatus["fedstylevalidator"] !== false && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-2">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-indigo-500" />
            Federal Style Validator — On-Save Validation
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            When enabled, the editor automatically runs a preflight validation pass after each
            document save and stores the quality score against the document. Disable for document
            types or workflows where FSV checks do not apply.
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleAutoValidation}
              disabled={savingAutoValidation}
              className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 ${
                autoValidationEnabled
                  ? "border-red-200 text-red-700 hover:bg-red-50"
                  : "border-green-200 text-green-700 hover:bg-green-50"
              }`}
            >
              {savingAutoValidation
                ? "Saving…"
                : autoValidationEnabled
                ? "Disable on-save validation"
                : "Enable on-save validation"}
            </button>
            <span className={`text-xs font-medium ${autoValidationEnabled ? "text-green-700" : "text-gray-500"}`}>
              {autoValidationEnabled ? "Currently enabled" : "Currently disabled"}
            </span>
          </div>
        </div>
      )}

      {/* FSV service URL — admin only */}
      {isAdmin && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Settings className="w-4 h-4 text-indigo-500" />
            Federal Style Validator — Service URL
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Set the base URL of a running FSV service instance. When configured, validation
            endpoints proxy to FSV instead of using internal implementations. Leave blank to use
            the built-in fallback or the <code>FEDERAL_STYLE_VALIDATOR_URL</code> environment variable.
          </p>
          <div className="flex items-center gap-2">
            <input
              type="url"
              value={fsvUrlInput}
              onChange={(e) => setFsvUrlInput(e.target.value)}
              placeholder="http://localhost:8080"
              className="flex-1 border border-gray-200 dark:border-gray-700 rounded-md px-3 py-1.5 text-xs bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
            />
            <button
              onClick={saveFsvUrl}
              disabled={savingFsvUrl || fsvUrlInput === fsvUrl}
              className="inline-flex items-center rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-40"
            >
              {savingFsvUrl ? "Saving…" : "Save"}
            </button>
          </div>
          {fsvUrl && (
            <div className="text-xs text-green-600">
              Active: <span className="font-mono">{fsvUrl}</span>
            </div>
          )}
        </div>
      )}

      {/* Per-check FSV category configuration — admin only, shown when FSV is active */}
      {isAdmin && builtinStatus["fedstylevalidator"] !== false && fsvCategories.length > 0 && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Settings className="w-4 h-4 text-indigo-500" />
            Federal Style Validator — Check Categories
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Enable or disable individual validation check categories. Disabled categories are
            skipped even when on-save validation is active.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {fsvCategories.map((category) => {
              const enabled = fsvChecks[category] !== false;
              const saving = savingFsvCheck === category;
              return (
                <div
                  key={category}
                  className="flex items-center justify-between rounded-md border border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2"
                >
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                    {formatCheckLabel(category)}
                  </span>
                  <button
                    onClick={() => toggleFsvCheck(category)}
                    disabled={saving}
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors disabled:opacity-40 ${
                      enabled
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                    title={enabled ? "Click to disable" : "Click to enable"}
                  >
                    {saving ? "…" : enabled ? "Enabled" : "Disabled"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
