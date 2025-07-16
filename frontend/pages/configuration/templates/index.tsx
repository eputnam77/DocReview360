import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Pencil, Trash, Eye, Download } from "lucide-react";

interface Template {
  id: string;
  name: string;
  docType?: string;
  format?: string;
  modified: string;
}

const DEMO_TEMPLATES: Template[] = [
  { id: "tpl1", name: "AC Template", docType: "Advisory Circular", format: "DOCX", modified: "2025-07-06" },
  { id: "tpl2", name: "Release Notes", docType: "Release Notes", format: "HTML", modified: "2025-07-05" },
];

export default function TemplatesIndex() {
  const [templates, setTemplates] = useState<Template[]>([]);

  useEffect(() => {
    fetch("/api/templates")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setTemplates(
          data.length
            ? data.map((t) => ({
                id: t.id || t.name,
                name: t.name,
                docType: t.docType,
                format: t.format || "—",
                modified: t.modified || t.updated || "—",
              }))
            : DEMO_TEMPLATES,
        )
      )
      .catch(() => setTemplates(DEMO_TEMPLATES));
  }, []);

  const removeTemplate = (id: string) =>
    setTemplates(templates.filter((t) => t.id !== id));

  const handleDownload = (tpl: Template) => {
    // If you have a download URL, use it; else, just alert for demo
    window.open(`/api/templates/${tpl.id}/download`, "_blank");
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
        <h1 className="text-2xl font-bold">Document Templates</h1>
        <Button asChild className="bg-indigo-600 hover:bg-indigo-700 text-white">
          <Link href="/configuration/templates/new">
            + Create Template
          </Link>
        </Button>
      </div>

      <Table className="min-w-full text-sm">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Document Type</TableHead>
            <TableHead>Format</TableHead>
            <TableHead>Modified</TableHead>
            <TableHead>Download</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {templates.map((t) => (
            <TableRow key={t.id} className="border-t last:border-none hover:bg-gray-50">
              <TableCell>{t.name}</TableCell>
              <TableCell>{t.docType || <span className="text-gray-400">—</span>}</TableCell>
              <TableCell>{t.format || <span className="text-gray-400">—</span>}</TableCell>
              <TableCell>{t.modified}</TableCell>
              <TableCell className="w-14">
                <Button
                  variant="ghost"
                  size="icon"
                  title="View or Download"
                  onClick={() => handleDownload(t)}
                >
                  {t.format && ["DOCX", "HTML", "XML", "JSON", "TXT"].includes(t.format)
                    ? <Download className="w-4 h-4" />
                    : <Eye className="w-4 h-4" />}
                </Button>
              </TableCell>
              <TableCell className="w-14">
                <Button variant="ghost" size="icon" asChild>
                  <Link href={`/configuration/templates/edit?id=${t.id}`} title="Edit">
                    <Pencil className="w-4 h-4" />
                  </Link>
                </Button>
              </TableCell>
              <TableCell className="w-14">
                <Button
                  variant="ghost"
                  size="icon"
                  title="Remove"
                  onClick={() => removeTemplate(t.id)}
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {templates.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-gray-400 py-10">
                No templates found.<br />
                <Button asChild className="mt-4 bg-indigo-600 hover:bg-indigo-700 text-white">
                  <Link href="/configuration/templates/new">
                    + Add your first template
                  </Link>
                </Button>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <div className="mt-4 text-xs text-gray-500">
        Templates are used to standardize document creation for each document type and editor. 
        <br />
        <b>Tip:</b> Click “Create Template” to add Word, HTML, JSON, or XML templates for your team to use.
      </div>
    </div>
  );
}
