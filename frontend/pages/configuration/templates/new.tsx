import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

export default function NewTemplatePage() {
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("");
  const [format, setFormat] = useState("JSON");
  const [content, setContent] = useState("");
  const [docTypes, setDocTypes] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/document-types")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => setDocTypes(data.map((d) => d.name)))
      .catch(() => setDocTypes([]));
  }, []);

  const handleSave = () => {
    const payload = { name, docType, format, content };
    // naive demo submission
    fetch("/api/templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {});

    alert("Template saved:\n" + JSON.stringify(payload, null, 2));
  };

  return (
    <div className="p-8 space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Create Template</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
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
                <SelectItem value="JSON">JSON</SelectItem>
                <SelectItem value="HTML">HTML</SelectItem>
                <SelectItem value="DOCX">DOCX</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <textarea
            className="w-full h-40 border rounded p-2"
            placeholder="Paste template content or leave blank to upload file"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <Button
            size="lg"
            onClick={handleSave}
            disabled={!name}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            Save Template
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
