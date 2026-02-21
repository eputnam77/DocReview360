"use client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, } from "@/components/ui/card";
import { FileInput } from "@/components/ui/file-input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { API } from "@/lib/api";
import { AlertCircle, BarChart3, Brain, CheckCircle, Download, FileText, Languages, Scale, Upload } from "lucide-react";
import React, { useEffect, useState } from "react";
const ANALYSIS_TOOLS = [
    {
        id: "textstat",
        name: "Readability Analysis",
        description: "Flesch-Kincaid scores, SMOG index, grade level",
        icon: <BarChart3 className="w-5 h-5"/>,
        color: "bg-blue-100 text-blue-800"
    },
    {
        id: "readability",
        name: "Reading Metrics",
        description: "ARI, Coleman-Liau, Gunning Fog indices",
        icon: <FileText className="w-5 h-5"/>,
        color: "bg-green-100 text-green-800"
    },
    {
        id: "textblob",
        name: "Sentiment Analysis",
        description: "Sentiment, language detection, noun phrases",
        icon: <Brain className="w-5 h-5"/>,
        color: "bg-purple-100 text-purple-800"
    },
    {
        id: "spacy",
        name: "NLP Analysis",
        description: "Named entities, POS tagging, dependencies",
        icon: <Languages className="w-5 h-5"/>,
        color: "bg-orange-100 text-orange-800"
    },
    {
        id: "lexnlp",
        name: "Legal Analysis",
        description: "Legal entities, dates, amounts, citations",
        icon: <Scale className="w-5 h-5"/>,
        color: "bg-indigo-100 text-indigo-800"
    }
];
export default function DocumentAnalysisPage() {
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedTools, setSelectedTools] = useState(["textstat"]);
    const [enabledTools, setEnabledTools] = useState([]);
    const [apiStatus, setApiStatus] = useState('unknown');
    useEffect(() => {
        const loadEnabledTools = async () => {
            try {
                const response = await fetch(`${API}/plugin-marketplace/builtin-status`);
                if (response.ok) {
                    const data = await response.json();
                    const enabled = ANALYSIS_TOOLS
                        .map(tool => tool.id)
                        .filter(toolId => data[toolId] === true);
                    setEnabledTools(enabled);
                    // Auto-select first enabled tool if none selected
                    if (enabled.length > 0 && selectedTools.length === 0) {
                        setSelectedTools([enabled[0]]);
                    }
                }
            }
            catch (error) {
                console.error("Failed to load enabled tools:", error);
                // Default to all tools enabled for development
                setEnabledTools(ANALYSIS_TOOLS.map(tool => tool.id));
            }
        };
        loadEnabledTools();
    }, []);
    const availableTools = ANALYSIS_TOOLS.filter(tool => enabledTools.includes(tool.id));
    const toggleTool = (toolId) => {
        setSelectedTools(prev => prev.includes(toolId)
            ? prev.filter(id => id !== toolId)
            : [...prev, toolId]);
    };
    async function handleSubmit(e) {
        e.preventDefault();
        if (selectedTools.length === 0) {
            setError("Please select at least one analysis tool");
            return;
        }
        setIsLoading(true);
        setError(null);
        setResults([]);
        const formData = new FormData(e.currentTarget);
        formData.append('tools', JSON.stringify(selectedTools));
        const apiUrl = API || '/api';
        try {
            console.log(`Submitting to: ${apiUrl}/tools/document-analysis`);
            const res = await fetch(`${apiUrl}/tools/document-analysis`, {
                method: "POST",
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                setResults(data.results || []);
                setApiStatus('connected');
            }
            else {
                const errorData = await res.json().catch(() => ({}));
                const errorMessage = errorData.error || `HTTP ${res.status}: ${res.statusText}`;
                setError(`Backend error: ${errorMessage}`);
                setApiStatus('disconnected');
            }
        }
        catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Network error';
            setError(`Connection error: ${errorMessage}`);
            setApiStatus('disconnected');
        }
        finally {
            setIsLoading(false);
        }
    }
    const getSuccessfulResults = () => results.filter(r => r.success);
    const getFailedResults = () => results.filter(r => !r.success);
    return (<div className="p-8 space-y-8">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Document Analysis</h1>
        <p className="text-gray-600">
          Analyze your documents with advanced readability metrics, sentiment analysis,
          and natural language processing tools.
        </p>
      </div>

      {/* API Status Indicator */}
      {apiStatus !== 'unknown' && (<Card className={`max-w-2xl ${apiStatus === 'connected' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              {apiStatus === 'connected' ? (<CheckCircle className="h-5 w-5 text-green-600"/>) : (<AlertCircle className="h-5 w-5 text-red-600"/>)}
              <span className={`text-sm font-medium ${apiStatus === 'connected' ? 'text-green-800' : 'text-red-800'}`}>
                {apiStatus === 'connected'
                ? 'Connected to document analysis backend'
                : 'Backend connection failed - check configuration'}
              </span>
            </div>
          </CardContent>
        </Card>)}

      {/* Tool Selection */}
      {availableTools.length > 0 && (<Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-indigo-600"/>
              Analysis Tools
            </CardTitle>
            <CardDescription>
              Select which analysis tools to run on your document
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              {availableTools.map((tool) => (<label key={tool.id} className={`flex items-center space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${selectedTools.includes(tool.id)
                    ? 'border-indigo-200 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'}`}>
                  <input type="checkbox" checked={selectedTools.includes(tool.id)} onChange={() => toggleTool(tool.id)} className="rounded"/>
                  <div className="flex items-center space-x-2">
                    {tool.icon}
                    <div>
                      <div className="font-medium">{tool.name}</div>
                      <div className="text-sm text-gray-500">{tool.description}</div>
                    </div>
                  </div>
                  <Badge className={`ml-auto text-xs ${tool.color}`}>
                    {tool.id}
                  </Badge>
                </label>))}
            </div>
          </CardContent>
        </Card>)}

      {/* Upload Card */}
      <Card className="max-w-2xl">
        <CardHeader className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-6 w-6 text-indigo-600"/>
            Upload Document
          </CardTitle>
          <CardDescription>
            Upload a text document (TXT, DOC, DOCX, PDF) for comprehensive analysis
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <FileInput name="file" accept=".txt,.doc,.docx,.pdf" required/>
            <Button type="submit" className="w-full" disabled={isLoading || selectedTools.length === 0}>
              {isLoading ? "Analyzing document..." : "Analyze Document"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (<Card className="border-red-200 bg-red-50 max-w-2xl">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <AlertCircle className="h-6 w-6 text-red-600"/>
            <CardTitle className="text-lg font-semibold text-red-800">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700">{error}</p>
            <div className="mt-4 text-sm text-red-600">
              <p><strong>Troubleshooting:</strong></p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Ensure the backend server is running</li>
                <li>Check that selected analysis tools are installed</li>
                <li>Verify file format is supported</li>
                <li>Check browser console for detailed error information</li>
              </ul>
            </div>
          </CardContent>
        </Card>)}

      {/* Successful Results */}
      {getSuccessfulResults().length > 0 && (<div className="space-y-4">
          <h2 className="text-xl font-semibold">Analysis Results</h2>
          <div className="grid gap-4">
            {getSuccessfulResults().map((result, index) => (<Card key={index}>
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <CheckCircle className="h-6 w-6 text-green-600"/>
                  <CardTitle className="text-lg font-semibold">
                    {ANALYSIS_TOOLS.find(t => t.id === result.tool)?.name || result.tool}
                  </CardTitle>
                  {result.downloadUrl && (<Button asChild variant="outline" size="sm" className="ml-auto">
                      <a href={result.downloadUrl}>
                        <Download className="h-4 w-4 mr-2"/>
                        Download
                      </a>
                    </Button>)}
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
              </Card>))}
          </div>
        </div>)}

      {/* Failed Results */}
      {getFailedResults().length > 0 && (<div className="space-y-4">
          <h2 className="text-xl font-semibold text-red-800">Failed Analyses</h2>
          <div className="grid gap-4">
            {getFailedResults().map((result, index) => (<Card key={index} className="border-red-200 bg-red-50">
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <AlertCircle className="h-6 w-6 text-red-600"/>
                  <CardTitle className="text-lg font-semibold text-red-800">
                    {ANALYSIS_TOOLS.find(t => t.id === result.tool)?.name || result.tool}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-red-700">{result.error}</p>
                </CardContent>
              </Card>))}
          </div>
        </div>)}

      {/* No Tools Available */}
      {availableTools.length === 0 && (<Card className="max-w-2xl border-yellow-200 bg-yellow-50">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <AlertCircle className="h-6 w-6 text-yellow-600"/>
            <CardTitle className="text-lg font-semibold text-yellow-800">No Analysis Tools Available</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-yellow-700 mb-4">
              No document analysis tools are currently enabled. Please install and enable analysis tools
              from the Plugin Marketplace to use this feature.
            </p>
            <Button asChild variant="outline">
              <a href="/configuration/plugin-marketplace">
                Go to Plugin Marketplace
              </a>
            </Button>
          </CardContent>
        </Card>)}
    </div>);
}
