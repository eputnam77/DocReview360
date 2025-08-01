// frontend/pages/editors/word.tsx
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { getAllWordTemplates, getWordTemplate, WordTemplate } from "@/data/templates/wordTemplates";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

/**
 * Word Template Viewer and Editor
 * Displays Word templates using Microsoft's Office Online viewer
 * Allows users to select from available templates and view them
 */
export default function WordEditorPage() {
  const router = useRouter();
  const [selectedTemplate, setSelectedTemplate] = useState<WordTemplate | null>(null);
  const [templates, setTemplates] = useState<WordTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load available templates
    const availableTemplates = getAllWordTemplates();
    setTemplates(availableTemplates);

    // Set default template if available
    if (availableTemplates.length > 0) {
      setSelectedTemplate(availableTemplates[0]);
    }
  }, []);

  // Handle template selection
  const handleTemplateSelect = (templateId: string) => {
    const template = getWordTemplate(templateId);
    if (template) {
      setSelectedTemplate(template);
      setError(null);
    }
  };

  // Generate Office Online viewer URL
  const getViewerUrl = (template: WordTemplate) => {
    if (!template) return "";

    // For development, use a sample document if the template file doesn't exist
    const baseUrl = process.env.NODE_ENV === 'development'
      ? 'https://file-examples.com/wp-content/uploads/2017/02/file-sample_100kB.docx'
      : `${window.location.origin}${template.url}`;

    return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(baseUrl)}`;
  };

  // Handle template download
  const handleDownload = (template: WordTemplate) => {
    if (!template) return;

    const link = document.createElement('a');
    link.href = template.url;
    link.download = `${template.id}.${template.type}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Handle template edit (opens in new window)
  const handleEdit = (template: WordTemplate) => {
    if (!template) return;

    const editUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(template.url)}&wdStartOn=1`;
    window.open(editUrl, '_blank');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Word Template Editor</h1>
          <p className="text-gray-600">
            View and edit Word templates using Microsoft Office Online
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Template Selection Sidebar */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Available Templates</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Template Category Filter */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Category
                  </label>
                  <Select onValueChange={(category) => {
                    const filtered = category === 'all'
                      ? getAllWordTemplates()
                      : getAllWordTemplates().filter(t => t.category === category);
                    setTemplates(filtered);
                  }}>
                    <SelectTrigger>
                      <SelectValue placeholder="All Categories" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Categories</SelectItem>
                      <SelectItem value="correspondence">Correspondence</SelectItem>
                      <SelectItem value="reports">Reports</SelectItem>
                      <SelectItem value="business">Business</SelectItem>
                      <SelectItem value="meetings">Meetings</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Template List */}
                <div className="space-y-2">
                  {templates.map((template) => (
                    <div
                      key={template.id}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedTemplate?.id === template.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => handleTemplateSelect(template.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-medium text-sm text-gray-900">
                            {template.label}
                          </h3>
                          <p className="text-xs text-gray-500 mt-1">
                            {template.description}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            <Badge variant="outline" className="text-xs">
                              {template.type.toUpperCase()}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {template.category}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Template Viewer */}
          <div className="lg:col-span-3">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">
                      {selectedTemplate ? selectedTemplate.label : 'Select a Template'}
                    </CardTitle>
                    {selectedTemplate && (
                      <p className="text-sm text-gray-500 mt-1">
                        {selectedTemplate.description}
                      </p>
                    )}
                  </div>
                  {selectedTemplate && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(selectedTemplate)}
                      >
                        Download
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleEdit(selectedTemplate)}
                      >
                        Edit Online
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {selectedTemplate ? (
                  <div className="space-y-4">
                    {/* Template Preview */}
                    <div className="border rounded-lg overflow-hidden">
                      <iframe
                        src={getViewerUrl(selectedTemplate)}
                        width="100%"
                        height="600"
                        frameBorder={0}
                        style={{
                          background: "#fff",
                        }}
                        allowFullScreen
                        title={`${selectedTemplate.label} Preview`}
                      />
                    </div>

                    {/* Template Info */}
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium text-sm text-gray-900 mb-2">
                        Template Information
                      </h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Type:</span>
                          <span className="ml-2 font-medium">{selectedTemplate.type.toUpperCase()}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Category:</span>
                          <span className="ml-2 font-medium capitalize">{selectedTemplate.category}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="text-gray-400 mb-4">
                      <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      No Template Selected
                    </h3>
                    <p className="text-gray-500">
                      Choose a template from the sidebar to preview it here
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
