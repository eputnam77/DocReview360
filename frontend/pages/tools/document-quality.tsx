"use client";

import { Badge } from "@/components/ui/badge";
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
import {
    AlertCircle,
    BookOpen,
    CheckCircle,
    Download,
    FileCheck,
    Shield,
    SpellCheck,
    Upload
} from "lucide-react";
import React, { useEffect, useState } from "react";

interface QualityResult {
  tool: string;
  success: boolean;
  data?: any;
  error?: string;
  downloadUrl?: string;
}

interface QualityResponse {
  results: QualityResult[];
  filename?: string;
  error?: string;
}

const QUALITY_TOOLS = [
  {
    id: "language-tool-python",
    name: "Grammar Checker",
    description: "Advanced grammar and style checking (30+ languages)",
    icon: <BookOpen className="w-5 h-5" />,
    color: "bg-green-100 text-green-800"
  },
  {
    id: "pyspellchecker",
    name: "Spell Checker",
    description: "Spell checking with correction suggestions",
    icon: <SpellCheck className="w-5 h-5" />,
    color: "bg-blue-100 text-blue-800"
  },
  {
    id: "gingerit",
    name: "Grammar Corrector",
    description: "Advanced grammar correction via Ginger API",
    icon: <FileCheck className="w-5 h-5" />,
    color: "bg-purple-100 text-purple-800"
  },
  {
    id: "govdocverify",
    name: "Accessibility Checker",
    description: "Document accessibility and compliance validation",
    icon: <Shield className="w-5 h-5" />,
    color: "bg-orange-100 text-orange-800",
    isBuiltIn: true
  }
];

export default function DocumentQualityPage() {
  const [results, setResults] = useState<QualityResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTools, setSelectedTools] = useState<string[]>(["pyspellchecker"]);
  const [enabledTools, setEnabledTools] = useState<string[]>([]);
  const [apiStatus, setApiStatus] = useState<'unknown' | 'connected' | 'disconnected'>('unknown');

  useEffect(() => {
    const loadEnabledTools = async () => {
      try {
        const response = await fetch(`${API}/plugin-marketplace/builtin-status`);
        if (response.ok) {
          const data = await response.json();
          const enabled = QUALITY_TOOLS
            .filter(tool => data[tool.id] === true || (tool.isBuiltIn && data[tool.id] !== false))
            .map(tool => tool.id);
          setEnabledTools(enabled);

          // Auto-select first enabled tool if none selected
          if (enabled.length > 0 && selectedTools.length === 0) {
            setSelectedTools([enabled[0]]);
          }
        }
      } catch (error) {
        console.error("Failed to load enabled tools:", error);
        // Default to built-in tools enabled for development
        setEnabledTools(QUALITY_TOOLS.filter(tool => tool.isBuiltIn).map(tool => tool.id));
      }
    };

    loadEnabledTools();
  }, []);

  const availableTools = QUALITY_TOOLS.filter(tool => enabledTools.includes(tool.id));

  const toggleTool = (toolId: string) => {
    setSelectedTools(prev =>
      prev.includes(toolId)
        ? prev.filter(id => id !== toolId)
        : [...prev, toolId]
    );
  };

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (selectedTools.length === 0) {
      setError("Please select at least one quality checker tool");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults([]);

    const formData = new FormData(e.currentTarget);
    formData.append('tools', JSON.stringify(selectedTools));
    const apiUrl = API || '/api';

    try {
      console.log(`Submitting to: ${apiUrl}/tools/document-quality`);
      const res = await fetch(`${apiUrl}/tools/document-quality`, {
        method: "POST",
        body: formData
      });

      if (res.ok) {
        const data: QualityResponse = await res.json();
        setResults(data.results || []);
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

  const getSuccessfulResults = () => results.filter(r => r.success);
  const getFailedResults = () => results.filter(r => !r.success);

  return (
    <div className="p-8 space-y-8">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Document Quality Checker</h1>
        <p className="text-gray-600">
          Check your documents for grammar errors, spelling mistakes, style issues,
          and accessibility compliance.
        </p>
      </div>

      {/* API Status Indicator */}
      {apiStatus !== 'unknown' && (
        <Card className={`max-w-2xl ${apiStatus === 'connected' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              {apiStatus === 'connected' ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600" />
              )}
              <span className={`text-sm font-medium ${apiStatus === 'connected' ? 'text-green-800' : 'text-red-800'}`}>
                {apiStatus === 'connected'
                  ? 'Connected to document quality backend'
                  : 'Backend connection failed - check configuration'
                }
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tool Selection */}
      {availableTools.length > 0 && (
        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-green-600" />
              Quality Checker Tools
            </CardTitle>
            <CardDescription>
              Select which quality checks to run on your document
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              {availableTools.map((tool) => (
                <label
                  key={tool.id}
                  className={`flex items-center space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedTools.includes(tool.id)
                      ? 'border-green-200 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedTools.includes(tool.id)}
                    onChange={() => toggleTool(tool.id)}
                    className="rounded"
                  />
                  <div className="flex items-center space-x-2">
                    {tool.icon}
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        {tool.name}
                        {tool.isBuiltIn && (
                          <Badge variant="default" className="text-xs">Built-in</Badge>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">{tool.description}</div>
                    </div>
                  </div>
                  <Badge className={`ml-auto text-xs ${tool.color}`}>
                    {tool.id.replace('-python', '').replace('language-tool', 'LT')}
                  </Badge>
                </label>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Card */}
      <Card className="max-w-2xl">
        <CardHeader className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-6 w-6 text-green-600" />
            Upload Document
          </CardTitle>
          <CardDescription>
            Upload a document (TXT, DOC, DOCX, PDF) for quality checking
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <FileInput
              name="file"
              accept=".txt,.doc,.docx,.pdf"
              required
            />
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || selectedTools.length === 0}
            >
              {isLoading ? "Checking document quality..." : "Check Document Quality"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className="border-red-200 bg-red-50 max-w-2xl">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <CardTitle className="text-lg font-semibold text-red-800">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700">{error}</p>
            <div className="mt-4 text-sm text-red-600">
              <p><strong>Troubleshooting:</strong></p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Ensure the backend server is running</li>
                <li>Check that selected quality tools are installed</li>
                <li>Verify file format is supported</li>
                <li>Check internet connection for external API tools</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Successful Results */}
      {getSuccessfulResults().length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Quality Check Results</h2>
          <div className="grid gap-4">
            {getSuccessfulResults().map((result, index) => (
              <Card key={index}>
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                  <CardTitle className="text-lg font-semibold">
                    {QUALITY_TOOLS.find(t => t.id === result.tool)?.name || result.tool}
                  </CardTitle>
                  {result.downloadUrl && (
                    <Button asChild variant="outline" size="sm" className="ml-auto">
                      <a href={result.downloadUrl}>
                        <Download className="h-4 w-4 mr-2" />
                        Download
                      </a>
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-64 rounded-md border p-4">
                    <pre className="whitespace-pre-wrap text-sm">
                      {typeof result.data === 'string'
                        ? result.data
                        : JSON.stringify(result.data, null, 2)}
                    </pre>
                  </ScrollArea>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Failed Results */}
      {getFailedResults().length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-red-800">Failed Quality Checks</h2>
          <div className="grid gap-4">
            {getFailedResults().map((result, index) => (
              <Card key={index} className="border-red-200 bg-red-50">
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                  <CardTitle className="text-lg font-semibold text-red-800">
                    {QUALITY_TOOLS.find(t => t.id === result.tool)?.name || result.tool}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-red-700">{result.error}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* No Tools Available */}
      {availableTools.length === 0 && (
        <Card className="max-w-2xl border-yellow-200 bg-yellow-50">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <AlertCircle className="h-6 w-6 text-yellow-600" />
            <CardTitle className="text-lg font-semibold text-yellow-800">No Quality Tools Available</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-yellow-700 mb-4">
              No document quality tools are currently enabled. Please install and enable quality checking tools
              from the Plugin Marketplace to use this feature.
            </p>
            <Button asChild variant="outline">
              <a href="/configuration/plugin-marketplace">
                Go to Plugin Marketplace
              </a>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
