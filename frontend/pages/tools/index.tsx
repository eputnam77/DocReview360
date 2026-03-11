import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";
import {
    BarChart3,
    FileCheck,
    FileCog,
    Settings,
    SpellCheck,
    Stamp
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

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
    label: "Document Checker",
    href: "/tools/checker",
    icon: <SpellCheck className="w-6 h-6 text-green-600" />,
    desc: "Validate documents with FedStyleValidator for FAA style and accessibility rules.",
    isBuiltIn: true,
    configHref: "/configuration/document-types",
  },
  {
    id: "scdocbuilder",
    label: "Special Conditions Doc Builder",
    href: "/tools/sc_converter",
    icon: <Stamp className="w-6 h-6 text-rose-600" />,
    desc: "Generate legally formatted Special Conditions notices.",
    isBuiltIn: true,
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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ToolsPage() {
  const [builtinStatus, setBuiltinStatus] = useState<Record<string, boolean>>({});
  const [installedPlugins, setInstalledPlugins] = useState<Set<string>>(new Set());
  const [communityPlugins, setCommunityPlugins] = useState<Set<string>>(new Set());
  const [toggling, setToggling] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
    </div>
  );
}
