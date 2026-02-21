import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API } from "@/lib/api";
import { BarChart3, // Icon for "Document Analysis"
FileCheck, FileCog, // Icon for "Document Quality"
Settings // Icon for "Document Processor"
, // Icon for "Converter"
SpellCheck, // Icon for "Checker"
Stamp } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
// List of all available tool items
const ALL_TOOLS_ITEMS = [
    {
        id: "converter",
        label: "Document Converter",
        href: "/tools/converter",
        icon: <FileCog className="w-6 h-6 text-indigo-600"/>,
        desc: "Convert Word, Markdown, and TipTap between formats.",
        isBuiltIn: false,
    },
    {
        id: "fedstylevalidator",
        label: "Document Checker",
        href: "/tools/checker",
        icon: <SpellCheck className="w-6 h-6 text-green-600"/>,
        desc: "Validate documents with FedStyleValidator for FAA style and accessibility rules.",
        isBuiltIn: true,
    },
    {
        id: "scdocbuilder",
        label: "Special Conditions Doc Builder",
        href: "/tools/sc_converter",
        icon: <Stamp className="w-6 h-6 text-rose-600"/>,
        desc: "Generate legally formatted Special Conditions notices.",
        isBuiltIn: true,
    },
    {
        id: "document-analysis",
        label: "Document Analysis",
        href: "/tools/document-analysis",
        icon: <BarChart3 className="w-6 h-6 text-blue-600"/>,
        desc: "Analyze readability, sentiment, and extract insights from documents.",
        isBuiltIn: false,
        requiresPlugins: ["textstat", "readability", "textblob", "spacy", "lexnlp"]
    },
    {
        id: "document-quality",
        label: "Document Quality Checker",
        href: "/tools/document-quality",
        icon: <FileCheck className="w-6 h-6 text-emerald-600"/>,
        desc: "Check grammar, spelling, style, and accessibility compliance.",
        isBuiltIn: false,
        requiresPlugins: ["language-tool-python", "pyspellchecker", "gingerit"],
        includesBuiltIn: ["fedstylevalidator"]
    },
    {
        id: "document-processor",
        label: "Document Processor",
        href: "/tools/document-processor",
        icon: <Settings className="w-6 h-6 text-purple-600"/>,
        desc: "Extract content, convert formats, and compare documents.",
        isBuiltIn: false,
        requiresPlugins: ["pdfplumber", "python-docx", "pypdf", "docling", "mammoth", "textdistance"]
    },
];
export default function ToolsPage() {
    const [enabledPlugins, setEnabledPlugins] = useState({});
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        const loadPluginStates = async () => {
            try {
                const response = await fetch(`${API}/plugin-marketplace/builtin-status`);
                if (response.ok) {
                    const data = await response.json();
                    setEnabledPlugins(data);
                }
                else {
                    // Default to enabled if API fails
                    setEnabledPlugins({
                        fedstylevalidator: true,
                        scdocbuilder: true
                    });
                }
            }
            catch (error) {
                // Default to enabled if API fails
                setEnabledPlugins({
                    fedstylevalidator: true,
                    scdocbuilder: true
                });
            }
            finally {
                setLoading(false);
            }
        };
        loadPluginStates();
    }, []);
    // Filter tools based on enabled state and plugin availability
    const visibleTools = ALL_TOOLS_ITEMS.filter(tool => {
        // Always show non-plugin-dependent tools
        if (!tool.isBuiltIn && !tool.requiresPlugins && !tool.includesBuiltIn) {
            return true;
        }
        // For built-in tools, check if they're enabled
        if (tool.isBuiltIn) {
            return enabledPlugins[tool.id] !== false;
        }
        // For plugin-dependent tools, check if at least one required plugin is enabled
        if (tool.requiresPlugins || tool.includesBuiltIn) {
            const requiredPlugins = tool.requiresPlugins || [];
            const builtInPlugins = tool.includesBuiltIn || [];
            const hasEnabledPlugin = requiredPlugins.some(pluginId => enabledPlugins[pluginId] === true);
            const hasEnabledBuiltIn = builtInPlugins.some(pluginId => enabledPlugins[pluginId] !== false);
            return hasEnabledPlugin || hasEnabledBuiltIn;
        }
        return true;
    });
    if (loading) {
        return (<div className="p-8 space-y-8">
        <h1 className="text-2xl font-bold">Tools</h1>
        <div className="flex items-center justify-center h-32">
          <div className="text-gray-500">Loading tools...</div>
        </div>
      </div>);
    }
    return (<div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Tools</h1>
      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
        {visibleTools.map((item) => (<Link key={item.href} href={item.href} className="group">
            <Card className="transition-shadow group-hover:shadow-lg h-full cursor-pointer">
              <CardHeader className="flex flex-row items-center gap-3 pb-2">
                {item.icon}
                <CardTitle className="text-lg font-semibold">
                  {item.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-500">{item.desc}</p>
              </CardContent>
            </Card>
          </Link>))}
      </div>

      {visibleTools.length === 0 && (<div className="text-center py-12">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No tools available</h3>
          <p className="text-gray-500">Contact your administrator to enable tools.</p>
        </div>)}
    </div>);
}
