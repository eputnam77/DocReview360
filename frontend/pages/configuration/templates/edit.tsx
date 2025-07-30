import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

const SUPPORTED_FORMATS = [
  { value: "DOCX", label: "Word DOCX (.docx)" },
  { value: "HTML", label: "HTML (.html)" },
  { value: "JSON", label: "JSON (.json)" },
  { value: "XML", label: "XML (.xml)" },
  { value: "TXT", label: "Plain Text / Markdown (.txt, .md)" },
];

// Demo fallback
const DEMO_TEMPLATE = {
  id: "tpl1",
  name: "AC Template",
  docType: "Advisory Circular",
  format: "HTML",
  content: "<h1>Title Here</h1><p>Content goes here...</p>",
};

export default function EditTemplatePage() {
  const router = useRouter();
  const { id } = router.query;

  const [name, setName] = useState("");
  const [docType, setDocType] = useState("");
  const [format, setFormat] = useState(SUPPORTED_FORMATS[0].value);
  const [content, setContent] = useState("");
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load doc types and template data
  useEffect(() => {
    fetch(`${API}/document-types`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => setDocTypes(data.map((d) => d.name)))
      .catch(() => setDocTypes([]));

    if (id) {
      // Replace with real API call: `/api/templates/${id}`
      // For demo, populate with static data
      setName(DEMO_TEMPLATE.name);
      setDocType(DEMO_TEMPLATE.docType);
      setFormat(DEMO_TEMPLATE.format || SUPPORTED_FORMATS[0].value);
      setContent(DEMO_TEMPLATE.content || "");
    }
  }, [id]);

  // File handling for editable text-based templates
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    setFile(selected || null);

    // Preview text for supported text formats
    if (
      selected &&
      ["txt", "md", "json", "xml", "html"].includes(
        selected.name.split(".").pop()?.toLowerCase() || ""
      )
    ) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setContent(event.target?.result as string);
      };
      reader.readAsText(selected);
    } else if (selected) {
      setContent("");
    }
  };

  const handleSave = async () => {
    let formData: FormData | undefined;
    let payload: any = { id, name, docType, format };

    if (file) {
      formData = new FormData();
      formData.append("file", file);
      formData.append("id", String(id));
      formData.append("name", name);
      formData.append("docType", docType);
      formData.append("format", format);
      if (content && ["TXT", "HTML", "JSON", "XML"].includes(format)) {
        formData.append("content", content);
      }
    } else {
      payload.content = content;
    }

    if (formData) {
      await fetch(`${API}/templates/${id}`, {
        method: "PUT",
        body: formData,
      });
    } else {
      await fetch(`${API}/templates/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    alert(
      "Template updated:\n" +
        JSON.stringify({ id, name, docType, format, file: file?.name, content: content ? "(see content)" : undefined }, null, 2)
    );
    // Optionally, redirect back to index
    // router.push("/configuration/templates");
  };

  return (
    <div className="p-8 space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Edit Document Template</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-gray-600 text-sm mb-2">
            Update the template for any supported editor (Word, HTML, etc.). You may upload a new file or edit the template content.
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Input
              placeholder="Template Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger>
                <SelectValue placeholder="Document Type (optional)" />
              </SelectTrigger>
              <SelectContent>
                {docTypes.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={format} onValueChange={setFormat}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SUPPORTED_FORMATS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Upload or paste */}
          <div className="space-y-2">
            <label className="block text-sm font-medium mb-1">Upload New Template File (optional)</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.html,.json,.xml,.txt,.md"
              onChange={handleFileChange}
            />
            <div className="text-xs text-gray-500">
              Upload a file to update this template (DOCX, HTML, JSON, XML, TXT, MD). For Word, upload .docx. For TipTap, use HTML or JSON.
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Edit Template Content
            </label>
            <textarea
              className="w-full h-40 border rounded p-2"
              placeholder="Paste or edit template content here. For Word, leave blank and upload .docx file."
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
            <div className="text-xs text-gray-500 mt-1">
              {format === "DOCX"
                ? "For Word templates, upload a .docx file. Text content is ignored."
                : "For HTML/JSON/XML/TXT, you can paste or edit the template here, or upload a file instead."}
            </div>
          </div>
          <Button
            size="lg"
            onClick={handleSave}
            disabled={!name}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            Update Template
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
