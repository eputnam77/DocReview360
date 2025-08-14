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
    Bot,
    CheckCircle,
    Code,
    Download,
    FileText,
    FileType,
    GitCompare,
    Settings,
    Upload
} from "lucide-react";
import React, { useEffect, useState } from "react";

interface ProcessorResult {
  tool: string;
  success: boolean;
  data?: any;
  error?: string;
  downloadUrl?: string;
}

interface ProcessorResponse {
  results: ProcessorResult[];
  filename?: string;
  error?: string;
}

const PROCESSOR_TOOLS = [
  {
    id: "pdfplumber",
    name: "PDF Extractor",
    description: "Extract text, tables, and metadata from PDFs",
    icon: <FileText className="w-5 h-5" />,
    color: "bg-red-100 text-red-800",
    accepts: ".pdf"
  },
  {
    id: "python-docx",
    name: "Word Processor",
    description: "Process DOCX files - extract text and structure",
    icon: <FileType className="w-5 h-5" />,
    color: "bg-blue-100 text-blue-800",
    accepts: ".docx,.doc"
  },
  {
    id: "pypdf",
    name: "PDF Manipulator",
    description: "Advanced PDF reading and manipulation",
    icon: <Settings className="w-5 h-5" />,
    color: "bg-purple-100 text-purple-800",
    accepts: ".pdf"
  },
  {
    id: "docling",
    name: "AI Document Parser",
    description: "AI-driven document conversion and analysis",
    icon: <Bot className="w-5 h-5" />,
    color: "bg-green-100 text-green-800",
    accepts: ".pdf,.docx,.doc,.txt"
  },
  {
    id: "mammoth",
    name: "DOCX to HTML",
    description: "Convert DOCX to clean, semantic HTML",
    icon: <Code className="w-5 h-5" />,
    color: "bg-orange-100 text-orange-800",
    accepts: ".docx"
  },
  {
    id: "textdistance",
    name: "Document Comparison",
    description: "Compare documents for similarity and differences",
    icon: <GitCompare className="w-5 h-5" />,
    color: "bg-indigo-100 text-indigo-800",
    accepts: ".txt,.docx,.pdf",
    requiresTwo: true
  }
];

export default function DocumentProcessorPage() {
  const [results, setResults] = useState<ProcessorResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTools, setSelectedTools] = useState<string[]>(["pdfplumber"]);
  const [enabledTools, setEnabledTools] = useState<string[]>([]);
  const [apiStatus, setApiStatus] = useState<'unknown' | 'connected' | 'disconnected'>('unknown');

  useEffect(() => {
    const loadEnabledTools = async () => {
      try {
        const response = await fetch(`${API}/plugin-marketplace/builtin-status`);
        if (response.ok) {
          const data = await response.json();
          const enabled = PROCESSOR_TOOLS
            .map(tool => tool.id)
            .filter(toolId => data[toolId] === true);
          setEnabledTools(enabled);

          // Auto-select first enabled tool if none selected
          if (enabled.length > 0 && selectedTools.length === 0) {
            setSelectedTools([enabled[0]]);
          }
        }
      } catch (error) {
        console.error("Failed to load enabled tools:", error);
        // Default to no tools enabled for development
        setEnabledTools([]);
      }
    };

    loadEnabledTools();
  }, []);

  const availableTools = PROCESSOR_TOOLS.filter(tool => enabledTools.includes(tool.id));

  const toggleTool = (toolId: string) => {
    setSelectedTools(prev =>
      prev.includes(toolId)
        ? prev.filter(id => id !== toolId)
        : [...prev, toolId]
    );
  };

  const getAcceptedFileTypes = () => {
    if (selectedTools.length === 0) return ".txt,.doc,.docx,.pdf";

    const selectedToolObjects = PROCESSOR_TOOLS.filter(tool => selectedTools.includes(tool.id));
    const allAccepts = selectedToolObjects.map(tool => tool.accepts).join(',');
    return [...new Set(allAccepts.split(','))].join(',');
  };

  const requiresTwoFiles = () => {
    return selectedTools.some(toolId =>
      PROCESSOR_TOOLS.find(tool => tool.id === toolId)?.requiresTwo
    );
  };

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (selectedTools.length === 0) {
      setError("Please select at least one processor tool");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults([]);

    const formData = new FormData(e.currentTarget);
    formData.append('tools', JSON.stringify(selectedTools));
    const apiUrl = API || '/api';

    try {
      console.log(`Submitting to: ${apiUrl}/tools/document-processor`);
      const res = await fetch(`${apiUrl}/tools/document-processor`, {
        method: "POST",
        body: formData
      });

      if (res.ok) {
        const data: ProcessorResponse = await res.json();
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
        <h1 className="text-2xl font-bold">Document Processor</h1>
        <p className="text-gray-600">
          Extract content, convert formats, compare documents, and perform advanced
          document processing operations.
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
                  ? 'Connected to document processor backend'
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
              <Settings className="w-5 h-5 text-purple-600" />
              Processing Tools
            </CardTitle>
            <CardDescription>
              Select which processing operations to perform on your document(s)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              {availableTools.map((tool) => (
                <label
                  key={tool.id}
                  className={`flex items-center space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedTools.includes(tool.id)
                      ? 'border-purple-200 bg-purple-50'
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
                        {tool.requiresTwo && (
                          <Badge variant="outline" className="text-xs">2 files</Badge>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">{tool.description}</div>
                      <div className="text-xs text-gray-400">Accepts: {tool.accepts}</div>
                    </div>
                  </div>
                  <Badge className={`ml-auto text-xs ${tool.color}`}>
                    {tool.id.replace('-', '')}
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
            <Upload className="h-6 w-6 text-purple-600" />
            Upload Document{requiresTwoFiles() ? 's' : ''}
          </CardTitle>
          <CardDescription>
            Upload document{requiresTwoFiles() ? 's' : ''} ({getAcceptedFileTypes()}) for processing
            {requiresTwoFiles() && (
              <span className="block text-orange-600 mt-1">
                Note: Document comparison requires two files
              </span>
            )}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <FileInput
              name="file"
              accept={getAcceptedFileTypes()}
              required
            />
            {requiresTwoFiles() && (
              <FileInput
                name="file2"
                accept={getAcceptedFileTypes()}
                required
                placeholder="Select second document for comparison..."
              />
            )}
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || selectedTools.length === 0}
            >
              {isLoading ? "Processing document..." : "Process Document"}
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
                <li>Check that selected processing tools are installed</li>
                <li>Verify file format matches selected tools</li>
                <li>For comparison tools, ensure both files are provided</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Successful Results */}
      {getSuccessfulResults().length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Processing Results</h2>
          <div className="grid gap-4">
            {getSuccessfulResults().map((result, index) => (
              <Card key={index}>
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                  <CardTitle className="text-lg font-semibold">
                    {PROCESSOR_TOOLS.find(t => t.id === result.tool)?.name || result.tool}
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
          <h2 className="text-xl font-semibold text-red-800">Failed Processing</h2>
          <div className="grid gap-4">
            {getFailedResults().map((result, index) => (
              <Card key={index} className="border-red-200 bg-red-50">
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                  <CardTitle className="text-lg font-semibold text-red-800">
                    {PROCESSOR_TOOLS.find(t => t.id === result.tool)?.name || result.tool}
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
            <CardTitle className="text-lg font-semibold text-yellow-800">No Processing Tools Available</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-yellow-700 mb-4">
              No document processing tools are currently enabled. Please install and enable processing tools
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
