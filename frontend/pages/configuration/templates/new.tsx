import React, { useState, useEffect, useRef } from "react";
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

export default function NewTemplatePage() {
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("");
  const [format, setFormat] = useState("DOCX");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API}/document-types`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => setDocTypes(data.map((d) => d.name)))
      .catch(() => setDocTypes([]));
  }, []);

  // When a file is selected, read its content (for preview or conversion)
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    setFile(selected || null);

    // Optionally, preview the content for text-based templates
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
    let payload: any = { name, docType, format };
    let formData: FormData | undefined;

    if (file) {
      formData = new FormData();
      formData.append("file", file);
      formData.append("name", name);
      formData.append("docType", docType);
      formData.append("format", format);
      // Optionally, also send pasted content for text formats
      if (content && ["TXT", "HTML", "JSON", "XML"].includes(format)) {
        formData.append("content", content);
      }
    } else {
      payload.content = content;
    }

    // Save via FormData if a file is included, otherwise JSON
    if (formData) {
      await fetch(`${API}/templates`, {
        method: "POST",
        body: formData,
      });
    } else {
      await fetch(`${API}/templates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    alert(
      "Template saved:\n" +
        JSON.stringify({ name, docType, format, file: file?.name, content: content ? "(see content)" : undefined }, null, 2)
    );
    setName("");
    setDocType("");
    setFormat("DOCX");
    setContent("");
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="p-8 space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Add Document Template</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-gray-600 text-sm">
            <div>
              Store templates for Advisory Circulars, Policy Statements, or any document type.
              Administrators may upload a file (Word, HTML, etc.) or paste template text for use in the document editor.
            </div>
            <ul className="list-disc ml-5 mt-2">
              <li>
                <b>Format:</b> Choose a template format matching your editor (e.g., DOCX for Word, HTML/JSON for TipTap).
              </li>
              <li>
                <b>Upload a file</b> or <b>paste the template content</b> below.
              </li>
              <li>
                When users create a new document, they’ll see the template for the selected doc type and editor.
              </li>
            </ul>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Input
              placeholder="Template Name (e.g. Advisory Circular v2)"
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
            <label className="block text-sm font-medium mb-1">Upload Template File</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.html,.json,.xml,.txt,.md"
              onChange={handleFileChange}
            />
            <div className="text-xs text-gray-500">
              Supported: DOCX, HTML, JSON, XML, TXT, Markdown. Upload a file <b>or</b> paste content below.
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Paste Template Content (optional)
            </label>
            <textarea
              className="w-full h-40 border rounded p-2"
              placeholder="Paste template content here. For Word, leave blank and upload .docx file."
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
          <Button
            size="lg"
            onClick={handleSave}
            disabled={!name || (!content && !file)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            Save Template
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
