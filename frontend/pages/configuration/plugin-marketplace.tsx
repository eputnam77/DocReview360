import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { API } from "@/lib/api";
import { Download, Info, PackagePlus } from "lucide-react";
import { useEffect, useState } from "react";

interface Plugin {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  author: string;
  tags: string[];
}

export default function PluginMarketplace() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/plugin-marketplace`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setPlugins(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        // Fallback to demo data if API fails
        setPlugins([
          {
            id: "grammar-plugin",
            name: "Grammar Plugin",
            description: "Advanced grammar checking and text validation for documents. Detects common writing issues like repeated words, basic grammar errors, and provides suggestions for improvement.",
            category: "Document Quality",
            version: "1.0.0",
            author: "DocReview360 Team",
            tags: ["grammar", "validation", "writing", "quality"]
          },
          {
            id: "demo-extension",
            name: "Demo Extension",
            description: "A demonstration plugin that shows how to create custom extensions for DocReview360. Useful for developers learning the plugin system.",
            category: "Development",
            version: "1.0.0",
            author: "DocReview360 Team",
            tags: ["demo", "development", "example"]
          }
        ]);
        setLoading(false);
      });
  }, []);

  const install = async (pluginId: string) => {
    setInstalling(pluginId);
    try {
      await fetch(`${API}/plugin-marketplace/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: pluginId }),
      });
      alert(`Successfully installed ${pluginId}`);
    } catch {
      alert("Install failed");
    } finally {
      setInstalling(null);
    }
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      "Document Quality": "bg-green-100 text-green-800",
      "Document Analysis": "bg-purple-100 text-purple-800",
      "Document Processing": "bg-blue-100 text-blue-800",
      "Document Export": "bg-orange-100 text-orange-800",
      "Development": "bg-gray-100 text-gray-800"
    };
    return colors[category] || "bg-gray-100 text-gray-800";
  };

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        <h1 className="text-2xl font-bold">Plugin Marketplace</h1>
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading plugins...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Plugin Marketplace</h1>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="space-y-2">
              <h3 className="font-semibold text-blue-900">About the Plugin Marketplace</h3>
              <p className="text-blue-800 text-sm">
                The Plugin Marketplace allows you to extend DocReview360's functionality with real PyPI packages.
                Each plugin provides specific features like advanced grammar checking, document analysis, PDF processing,
                and enhanced export capabilities. These are actual Python packages that integrate seamlessly with the core system.
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
        {plugins.map((plugin) => (
          <Card key={plugin.id} className="h-full flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  <PackagePlus className="w-5 h-5 text-blue-600" />
                  <CardTitle className="text-lg">{plugin.name}</CardTitle>
                </div>
                <Badge variant="outline" className="text-xs">
                  v{plugin.version}
                </Badge>
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
                {plugin.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>

            <CardFooter className="pt-3">
              <Button
                onClick={() => install(plugin.id)}
                disabled={installing === plugin.id}
                className="w-full"
                size="sm"
              >
                {installing === plugin.id ? (
                  <>
                    <Download className="w-4 h-4 mr-2 animate-pulse" />
                    Installing...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Install Plugin
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {plugins.length === 0 && (
        <div className="text-center py-12">
          <PackagePlus className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No plugins available</h3>
          <p className="text-gray-500">Check back later for new plugins or contact your administrator.</p>
        </div>
      )}
    </div>
  );
}
