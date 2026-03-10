import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authenticatedFetch } from "@/lib/api";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { toast } from "react-hot-toast";

const SUPPORTED_FORMATS = [
  { value: "DOCX", label: "Word DOCX (.docx)" },
  { value: "HTML", label: "HTML (.html)" },
  { value: "JSON", label: "JSON (.json)" },
  { value: "XML", label: "XML (.xml)" },
  { value: "TXT", label: "Plain Text / Markdown (.txt, .md)" },
];

export default function EditTemplatePage() {
  const router = useRouter();
  const { id } = router.query;

  const [name, setName] = useState("");
  const [docType, setDocType] = useState("");
  const [format, setFormat] = useState(SUPPORTED_FORMATS[0].value);
  const [content, setContent] = useState("");
  const [version, setVersion] = useState<number | null>(null);
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load doc types and template data
  useEffect(() => {
    authenticatedFetch(`/document-types`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => setDocTypes(data.map((d) => d.name)))
      .catch(() => setDocTypes([]));

    if (id) {
      authenticatedFetch(`/templates/${id}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((tpl) => {
          if (!tpl) return;
          setName(tpl.name || tpl.id || "");
          setDocType(tpl.docType || tpl.doc_type || "");
          setFormat(
            (tpl.format || tpl.type || SUPPORTED_FORMATS[0].value).toUpperCase(),
          );
          setContent(tpl.content || "");
          setVersion(typeof tpl.version === "number" ? tpl.version : null);
        })
        .catch(() => {
          /* ignore fetch errors - keep defaults */
        });
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
      await authenticatedFetch(`/templates/${id}`, {
        method: "PUT",
        body: formData,
      });
    } else {
      await authenticatedFetch(`/templates/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    toast.success(
      "Template updated:\n" +
        JSON.stringify(
          {
            id,
            name,
            docType,
            format,
            file: file?.name,
            content: content ? "(see content)" : undefined,
          },
          null,
          2,
        ),
    );
    // Optionally, redirect back to index
    // router.push("/configuration/templates");
  };

  return (
    <div className="p-8 space-y-8">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <CardTitle className="text-2xl font-bold">Edit Document Template</CardTitle>
            {version !== null && (
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
                v{version}
              </span>
            )}
          </div>
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
