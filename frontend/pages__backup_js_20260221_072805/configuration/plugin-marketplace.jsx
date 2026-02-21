import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { API } from "@/lib/api";
import { Download, Info, PackagePlus, Settings, ToggleLeft, ToggleRight } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
export default function PluginMarketplace() {
    const [plugins, setPlugins] = useState([]);
    const [loading, setLoading] = useState(true);
    const [installing, setInstalling] = useState(null);
    const [toggling, setToggling] = useState(null);
    useEffect(() => {
        const loadPlugins = async () => {
            try {
                // First try to fetch marketplace plugins
                const marketplaceResponse = await fetch(`${API}/plugin-marketplace`);
                const marketplaceData = marketplaceResponse.ok ? await marketplaceResponse.json() : [];
                // Then fetch built-in plugin states
                const builtInResponse = await fetch(`${API}/plugin-marketplace/builtin-status`);
                const builtInData = builtInResponse.ok ? await builtInResponse.json() : {};
                // Built-in plugins that are always available
                const builtInPlugins = [
                    {
                        id: "fedstylevalidator",
                        name: "FedStyleValidator",
                        description: "Federal Style Validator for government documents. Validates FAA style guidelines, accessibility standards, and regulatory compliance requirements. Provides detailed feedback on heading structure, formatting, and content validation.",
                        category: "Document Quality",
                        version: "2.1.0",
                        author: "DocReview360 Team",
                        tags: ["government", "verification", "faa", "accessibility", "compliance"],
                        isBuiltIn: true,
                        isEnabled: builtInData.fedstylevalidator !== false // Default to enabled
                    },
                    {
                        id: "scdocbuilder",
                        name: "SCDocBuilder",
                        description: "Special Conditions Document Builder for generating legally formatted FAA Special Conditions notices. Automates the creation of regulatory documents with proper formatting, numbering, and compliance validation.",
                        category: "Document Processing",
                        version: "1.5.0",
                        author: "DocReview360 Team",
                        tags: ["special-conditions", "faa", "regulatory", "legal", "automation"],
                        isBuiltIn: true,
                        isEnabled: builtInData.scdocbuilder !== false // Default to enabled
                    }
                ];
                // PyPI plugins available for installation
                const pypiPlugins = [
                    // Document Analysis Tools
                    {
                        id: "textstat",
                        name: "TextStat",
                        description: "Comprehensive readability analysis tool that calculates Flesch-Kincaid scores, SMOG index, word count, sentence complexity, and grade-level assessments for any text document.",
                        category: "Document Analysis",
                        version: "0.7.3",
                        author: "PyPI Community",
                        tags: ["readability", "statistics", "analysis", "metrics", "flesch-kincaid"],
                        isEnabled: builtInData.textstat === true // Default to disabled
                    },
                    {
                        id: "readability",
                        name: "Readability",
                        description: "Advanced reading level analysis providing multiple readability metrics including ARI, Coleman-Liau, and Gunning Fog indices for comprehensive document assessment.",
                        category: "Document Analysis",
                        version: "0.3.1",
                        author: "PyPI Community",
                        tags: ["readability", "metrics", "analysis", "ari", "coleman-liau"],
                        isEnabled: builtInData.readability === true // Default to disabled
                    },
                    {
                        id: "textblob",
                        name: "TextBlob",
                        description: "Natural language processing tool for sentiment analysis, noun phrase extraction, language detection, and basic linguistic analysis of text documents.",
                        category: "Document Analysis",
                        version: "0.17.1",
                        author: "PyPI Community",
                        tags: ["nlp", "sentiment", "language-detection", "linguistics", "analysis"],
                        isEnabled: builtInData.textblob === true // Default to disabled
                    },
                    {
                        id: "spacy",
                        name: "spaCy",
                        description: "Industrial-strength natural language processing for named entity recognition, part-of-speech tagging, dependency parsing, and advanced document analysis.",
                        category: "Document Analysis",
                        version: "3.7.2",
                        author: "PyPI Community",
                        tags: ["nlp", "entities", "pos-tagging", "parsing", "advanced"],
                        isEnabled: builtInData.spacy === true // Default to disabled
                    },
                    {
                        id: "lexnlp",
                        name: "LexNLP",
                        description: "Specialized NLP library for legal and regulatory documents. Extracts entities, dates, amounts, citations, and legal-specific information from text.",
                        category: "Document Analysis",
                        version: "2.3.0",
                        author: "PyPI Community",
                        tags: ["legal", "regulatory", "entities", "citations", "compliance"],
                        isEnabled: builtInData.lexnlp === true // Default to disabled
                    },
                    // Document Quality Tools
                    {
                        id: "language-tool-python",
                        name: "LanguageTool Python",
                        description: "Grammar and style checker supporting 30+ languages. Detects grammar errors, style issues, and provides detailed correction suggestions.",
                        category: "Document Quality",
                        version: "2.7.1",
                        author: "PyPI Community",
                        tags: ["grammar", "style", "proofreading", "multilingual", "corrections"],
                        isEnabled: builtInData["language-tool-python"] === true // Default to disabled
                    },
                    {
                        id: "pyspellchecker",
                        name: "PySpellChecker",
                        description: "Pure Python spell checker with word frequency analysis. Provides spell checking and correction suggestions for multiple languages.",
                        category: "Document Quality",
                        version: "0.7.2",
                        author: "PyPI Community",
                        tags: ["spelling", "corrections", "multilingual", "frequency", "dictionary"],
                        isEnabled: builtInData.pyspellchecker === true // Default to disabled
                    },
                    {
                        id: "gingerit",
                        name: "GingerIt",
                        description: "Grammar correction API wrapper that provides advanced grammar checking and text improvement suggestions using the Ginger API.",
                        category: "Document Quality",
                        version: "0.8.1",
                        author: "PyPI Community",
                        tags: ["grammar", "corrections", "api", "improvement", "suggestions"],
                        isEnabled: builtInData.gingerit === true // Default to disabled
                    },
                    // Document Processing Tools
                    {
                        id: "pdfplumber",
                        name: "PDFPlumber",
                        description: "Advanced PDF text extraction and analysis tool. Extracts text, tables, metadata, and provides detailed layout information from PDF documents.",
                        category: "Document Processing",
                        version: "0.10.3",
                        author: "PyPI Community",
                        tags: ["pdf", "extraction", "tables", "metadata", "layout"],
                        isEnabled: builtInData.pdfplumber === true // Default to disabled
                    },
                    {
                        id: "python-docx",
                        name: "Python-docx",
                        description: "Microsoft Word document processor for reading, writing, and analyzing DOCX files. Provides access to document structure, styles, and content.",
                        category: "Document Processing",
                        version: "0.8.11",
                        author: "PyPI Community",
                        tags: ["docx", "word", "microsoft", "structure", "content"],
                        isEnabled: builtInData["python-docx"] === true // Default to disabled
                    },
                    {
                        id: "pypdf",
                        name: "PyPDF",
                        description: "Pure Python PDF library for reading, writing, and manipulating PDF documents. Supports text extraction, page manipulation, and metadata editing.",
                        category: "Document Processing",
                        version: "3.17.4",
                        author: "PyPI Community",
                        tags: ["pdf", "manipulation", "extraction", "metadata", "pages"],
                        isEnabled: builtInData.pypdf === true // Default to disabled
                    },
                    {
                        id: "docling",
                        name: "Docling",
                        description: "AI-driven document conversion toolkit that parses various document formats into unified, structured representations for analysis and processing.",
                        category: "Document Processing",
                        version: "1.0.2",
                        author: "PyPI Community",
                        tags: ["ai", "conversion", "parsing", "structured", "formats"],
                        isEnabled: builtInData.docling === true // Default to disabled
                    },
                    {
                        id: "mammoth",
                        name: "Mammoth",
                        description: "DOCX to HTML converter that produces clean, semantic HTML while preserving document structure and formatting for web-based document analysis.",
                        category: "Document Processing",
                        version: "1.6.0",
                        author: "PyPI Community",
                        tags: ["docx", "html", "conversion", "semantic", "structure"],
                        isEnabled: builtInData.mammoth === true // Default to disabled
                    },
                    {
                        id: "textdistance",
                        name: "TextDistance",
                        description: "Document comparison tool with 30+ similarity algorithms. Compare documents for plagiarism detection, version differences, and content similarity analysis.",
                        category: "Document Processing",
                        version: "4.6.0",
                        author: "PyPI Community",
                        tags: ["comparison", "similarity", "plagiarism", "algorithms", "analysis"],
                        isEnabled: builtInData.textdistance === true // Default to disabled
                    }
                ];
                // Combine marketplace, built-in, and PyPI plugins
                const allPlugins = [
                    ...builtInPlugins,
                    ...pypiPlugins,
                    ...(Array.isArray(marketplaceData) ? marketplaceData : [])
                ];
                setPlugins(allPlugins);
            }
            catch (error) {
                // Fallback to sample data if API fails
                setPlugins([
                    {
                        id: "fedstylevalidator",
                        name: "FedStyleValidator",
                        description: "Federal Style Validator for government documents. Validates FAA style guidelines, accessibility standards, and regulatory compliance requirements. Provides detailed feedback on heading structure, formatting, and content validation.",
                        category: "Document Quality",
                        version: "2.1.0",
                        author: "DocReview360 Team",
                        tags: ["government", "verification", "faa", "accessibility", "compliance"],
                        isBuiltIn: true,
                        isEnabled: true
                    },
                    {
                        id: "scdocbuilder",
                        name: "SCDocBuilder",
                        description: "Special Conditions Document Builder for generating legally formatted FAA Special Conditions notices. Automates the creation of regulatory documents with proper formatting, numbering, and compliance validation.",
                        category: "Document Processing",
                        version: "1.5.0",
                        author: "DocReview360 Team",
                        tags: ["special-conditions", "faa", "regulatory", "legal", "automation"],
                        isBuiltIn: true,
                        isEnabled: true
                    },
                    // Document Analysis Tools
                    {
                        id: "textstat",
                        name: "TextStat",
                        description: "Comprehensive readability analysis tool that calculates Flesch-Kincaid scores, SMOG index, word count, sentence complexity, and grade-level assessments for any text document.",
                        category: "Document Analysis",
                        version: "0.7.3",
                        author: "PyPI Community",
                        tags: ["readability", "statistics", "analysis", "metrics", "flesch-kincaid"]
                    },
                    {
                        id: "readability",
                        name: "Readability",
                        description: "Advanced reading level analysis providing multiple readability metrics including ARI, Coleman-Liau, and Gunning Fog indices for comprehensive document assessment.",
                        category: "Document Analysis",
                        version: "0.3.1",
                        author: "PyPI Community",
                        tags: ["readability", "metrics", "analysis", "ari", "coleman-liau"]
                    },
                    {
                        id: "textblob",
                        name: "TextBlob",
                        description: "Natural language processing tool for sentiment analysis, noun phrase extraction, language detection, and basic linguistic analysis of text documents.",
                        category: "Document Analysis",
                        version: "0.17.1",
                        author: "PyPI Community",
                        tags: ["nlp", "sentiment", "language-detection", "linguistics", "analysis"]
                    },
                    {
                        id: "spacy",
                        name: "spaCy",
                        description: "Industrial-strength natural language processing for named entity recognition, part-of-speech tagging, dependency parsing, and advanced document analysis.",
                        category: "Document Analysis",
                        version: "3.7.2",
                        author: "PyPI Community",
                        tags: ["nlp", "entities", "pos-tagging", "parsing", "advanced"]
                    },
                    {
                        id: "lexnlp",
                        name: "LexNLP",
                        description: "Specialized NLP library for legal and regulatory documents. Extracts entities, dates, amounts, citations, and legal-specific information from text.",
                        category: "Document Analysis",
                        version: "2.3.0",
                        author: "PyPI Community",
                        tags: ["legal", "regulatory", "entities", "citations", "compliance"]
                    },
                    // Document Quality Tools
                    {
                        id: "language-tool-python",
                        name: "LanguageTool Python",
                        description: "Grammar and style checker supporting 30+ languages. Detects grammar errors, style issues, and provides detailed correction suggestions.",
                        category: "Document Quality",
                        version: "2.7.1",
                        author: "PyPI Community",
                        tags: ["grammar", "style", "proofreading", "multilingual", "corrections"]
                    },
                    {
                        id: "pyspellchecker",
                        name: "PySpellChecker",
                        description: "Pure Python spell checker with word frequency analysis. Provides spell checking and correction suggestions for multiple languages.",
                        category: "Document Quality",
                        version: "0.7.2",
                        author: "PyPI Community",
                        tags: ["spelling", "corrections", "multilingual", "frequency", "dictionary"]
                    },
                    {
                        id: "gingerit",
                        name: "GingerIt",
                        description: "Grammar correction API wrapper that provides advanced grammar checking and text improvement suggestions using the Ginger API.",
                        category: "Document Quality",
                        version: "0.8.1",
                        author: "PyPI Community",
                        tags: ["grammar", "corrections", "api", "improvement", "suggestions"]
                    },
                    // Document Processing Tools
                    {
                        id: "pdfplumber",
                        name: "PDFPlumber",
                        description: "Advanced PDF text extraction and analysis tool. Extracts text, tables, metadata, and provides detailed layout information from PDF documents.",
                        category: "Document Processing",
                        version: "0.10.3",
                        author: "PyPI Community",
                        tags: ["pdf", "extraction", "tables", "metadata", "layout"]
                    },
                    {
                        id: "python-docx",
                        name: "Python-docx",
                        description: "Microsoft Word document processor for reading, writing, and analyzing DOCX files. Provides access to document structure, styles, and content.",
                        category: "Document Processing",
                        version: "0.8.11",
                        author: "PyPI Community",
                        tags: ["docx", "word", "microsoft", "structure", "content"]
                    },
                    {
                        id: "pypdf",
                        name: "PyPDF",
                        description: "Pure Python PDF library for reading, writing, and manipulating PDF documents. Supports text extraction, page manipulation, and metadata editing.",
                        category: "Document Processing",
                        version: "3.17.4",
                        author: "PyPI Community",
                        tags: ["pdf", "manipulation", "extraction", "metadata", "pages"]
                    },
                    {
                        id: "docling",
                        name: "Docling",
                        description: "AI-driven document conversion toolkit that parses various document formats into unified, structured representations for analysis and processing.",
                        category: "Document Processing",
                        version: "1.0.2",
                        author: "PyPI Community",
                        tags: ["ai", "conversion", "parsing", "structured", "formats"]
                    },
                    {
                        id: "mammoth",
                        name: "Mammoth",
                        description: "DOCX to HTML converter that produces clean, semantic HTML while preserving document structure and formatting for web-based document analysis.",
                        category: "Document Processing",
                        version: "1.6.0",
                        author: "PyPI Community",
                        tags: ["docx", "html", "conversion", "semantic", "structure"]
                    },
                    {
                        id: "textdistance",
                        name: "TextDistance",
                        description: "Document comparison tool with 30+ similarity algorithms. Compare documents for plagiarism detection, version differences, and content similarity analysis.",
                        category: "Document Processing",
                        version: "4.6.0",
                        author: "PyPI Community",
                        tags: ["comparison", "similarity", "plagiarism", "algorithms", "analysis"]
                    },
                ]);
            }
            finally {
                setLoading(false);
            }
        };
        loadPlugins();
    }, []);
    const install = async (pluginId) => {
        setInstalling(pluginId);
        try {
            await fetch(`${API}/plugin-marketplace/install`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: pluginId }),
            });
            toast.success(`Successfully installed ${pluginId}`);
        }
        catch {
            toast.error("Install failed");
        }
        finally {
            setInstalling(null);
        }
    };
    const togglePlugin = async (pluginId, currentState) => {
        setToggling(pluginId);
        try {
            await fetch(`${API}/plugin-marketplace/toggle`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    pluginId,
                    enabled: !currentState
                }),
            });
            // Update local state
            setPlugins(plugins.map(plugin => plugin.id === pluginId
                ? { ...plugin, isEnabled: !currentState }
                : plugin));
            toast.success(`${!currentState ? 'Enabled' : 'Disabled'} ${pluginId} in Tool menus`);
        }
        catch {
            toast.error("Toggle failed");
        }
        finally {
            setToggling(null);
        }
    };
    const getCategoryColor = (category) => {
        const colors = {
            "Document Quality": "bg-green-100 text-green-800",
            "Document Analysis": "bg-purple-100 text-purple-800",
            "Document Processing": "bg-blue-100 text-blue-800",
            "Document Export": "bg-orange-100 text-orange-800",
            "Development": "bg-gray-100 text-gray-800"
        };
        return colors[category] || "bg-gray-100 text-gray-800";
    };
    if (loading) {
        return (<div className="p-8 space-y-6">
        <h1 className="text-2xl font-bold">Plugin Marketplace</h1>
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading plugins...</div>
        </div>
      </div>);
    }
    return (<div className="p-8 space-y-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Plugin Marketplace</h1>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0"/>
            <div className="space-y-2">
              <h3 className="font-semibold text-blue-900">About the Plugin Marketplace</h3>
              <p className="text-blue-800 text-sm">
                The Plugin Marketplace allows you to extend DocReview360's functionality with real PyPI packages and manage built-in tools.
                Each plugin provides specific features like advanced grammar checking, document analysis, PDF processing,
                and enhanced export capabilities. These are actual Python packages that integrate seamlessly with the core system.
              </p>
              <p className="text-blue-700 text-sm">
                <strong>Built-in Tools:</strong> FedStyleValidator and SCDocBuilder are pre-installed tools that can be toggled on/off
                in the Tool menus. These tools are always available but can be hidden from navigation if not needed.
              </p>
              <p className="text-blue-700 text-sm">
                <strong>Note:</strong> Plugin installation requires appropriate permissions and downloads packages from PyPI.
                Some plugins may require additional system dependencies or a restart to take full effect.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {plugins.map((plugin) => (<Card key={plugin.id} className="h-full flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  {plugin.isBuiltIn ? (<Settings className="w-5 h-5 text-indigo-600"/>) : (<PackagePlus className="w-5 h-5 text-blue-600"/>)}
                  <CardTitle className="text-lg">{plugin.name}</CardTitle>
                </div>
                <div className="flex items-center space-x-2">
                  {plugin.isBuiltIn && (<Badge variant="default" className="text-xs">
                      Built-in
                    </Badge>)}
                  <Badge variant="outline" className="text-xs">
                    v{plugin.version}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <Badge className={`text-xs ${getCategoryColor(plugin.category)}`}>
                  {plugin.category}
                </Badge>
                <span className="text-xs text-gray-500">by {plugin.author}</span>
              </div>
            </CardHeader>

            <CardContent className="flex-grow">
              <p className="text-sm text-gray-600 mb-4">
                {plugin.description}
              </p>

              <div className="flex flex-wrap gap-1">
                {plugin.tags.map((tag) => (<Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>))}
              </div>
            </CardContent>

            <CardFooter className="pt-3">
              {plugin.isBuiltIn ? (<div className="w-full space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">
                      Show in Tool menus
                    </span>
                    <Button onClick={() => togglePlugin(plugin.id, plugin.isEnabled || false)} disabled={toggling === plugin.id} variant="ghost" size="sm" className="p-1">
                      {toggling === plugin.id ? (<Settings className="w-5 h-5 animate-pulse text-gray-400"/>) : plugin.isEnabled ? (<ToggleRight className="w-5 h-5 text-green-600"/>) : (<ToggleLeft className="w-5 h-5 text-gray-400"/>)}
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500">
                    {plugin.isEnabled ? 'Visible in Tool menus' : 'Hidden from Tool menus'}
                  </p>
                </div>) : plugin.author === "PyPI Community" ? (<div className="w-full space-y-2">
                  <Button onClick={() => install(plugin.id)} disabled={installing === plugin.id} className="w-full" size="sm" variant={plugin.isEnabled ? "outline" : "default"}>
                    {installing === plugin.id ? (<>
                        <Download className="w-4 h-4 mr-2 animate-pulse"/>
                        Installing...
                      </>) : plugin.isEnabled ? (<>
                        <Download className="w-4 h-4 mr-2"/>
                        Reinstall
                      </>) : (<>
                        <Download className="w-4 h-4 mr-2"/>
                        Install from PyPI
                      </>)}
                  </Button>
                  {plugin.isEnabled && (<div className="flex items-center justify-between">
                      <span className="text-xs text-gray-600">
                        Show in Tool menus
                      </span>
                      <Button onClick={() => togglePlugin(plugin.id, plugin.isEnabled || false)} disabled={toggling === plugin.id} variant="ghost" size="sm" className="p-1">
                        {toggling === plugin.id ? (<Settings className="w-5 h-5 animate-pulse text-gray-400"/>) : plugin.isEnabled ? (<ToggleRight className="w-5 h-5 text-green-600"/>) : (<ToggleLeft className="w-5 h-5 text-gray-400"/>)}
                      </Button>
                    </div>)}
                </div>) : (<Button onClick={() => install(plugin.id)} disabled={installing === plugin.id} className="w-full" size="sm">
                  {installing === plugin.id ? (<>
                      <Download className="w-4 h-4 mr-2 animate-pulse"/>
                      Installing...
                    </>) : (<>
                      <Download className="w-4 h-4 mr-2"/>
                      Install Plugin
                    </>)}
                </Button>)}
            </CardFooter>
          </Card>))}
      </div>

      {plugins.length === 0 && (<div className="text-center py-12">
          <PackagePlus className="w-12 h-12 text-gray-400 mx-auto mb-4"/>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No plugins available</h3>
          <p className="text-gray-500">Check back later for new plugins or contact your administrator.</p>
        </div>)}
    </div>);
}
