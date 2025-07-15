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
import { Pencil, Trash } from "lucide-react";

interface Template {
  id: string;
  name: string;
  docType?: string;
  modified: string;
}

const DEMO_TEMPLATES: Template[] = [
  { id: "tpl1", name: "AC Template", docType: "Advisory Circular", modified: "2025-07-06" },
  { id: "tpl2", name: "Release Notes", docType: "Release Notes", modified: "2025-07-05" },
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
                modified: t.modified || t.updated || "—",
              }))
            : DEMO_TEMPLATES,
        )
      )
      .catch(() => setTemplates(DEMO_TEMPLATES));
  }, []);

  const removeTemplate = (id: string) =>
    setTemplates(templates.filter((t) => t.id !== id));

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Templates</h1>
        <Button asChild>
          <Link href="/configuration/templates/new">Create Template</Link>
        </Button>
      </div>
      <Table className="min-w-full text-sm">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Document Type</TableHead>
            <TableHead>Modified</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {templates.map((t) => (
            <TableRow key={t.id} className="border-t last:border-none hover:bg-gray-50">
              <TableCell>{t.name}</TableCell>
              <TableCell>{t.docType || <span className="text-gray-400">—</span>}</TableCell>
              <TableCell>{t.modified}</TableCell>
              <TableCell className="w-12">
                <Button variant="ghost" size="icon" asChild>
                  <Link href={`/configuration/templates/edit?id=${t.id}`} title="Edit">
                    <Pencil className="w-4 h-4" />
                  </Link>
                </Button>
              </TableCell>
              <TableCell className="w-12">
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
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No templates defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
