import React, { useEffect, useMemo, useState } from "react";
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
import { Pencil, Trash, Eye, Download, CheckCircle, Archive } from "lucide-react";
import { API, authenticatedFetch } from "@/lib/api";
import { buildTemplateUrlPath } from "@/lib/templatePath";
import { toast } from "react-hot-toast";

interface Template {
  id: string;
  name: string;
  docType?: string;
  format?: string;
  modified: string;
  approved: boolean;
  retired: boolean;
}

interface EmailTemplate {
  name: string;
  subject: string;
  task?: string;
}

export function createTemplateConfigApi() {
  return {
    listTemplates: () => authenticatedFetch(`${API}/templates`),
    listEmailTemplates: () => authenticatedFetch(`${API}/email-templates`),
    deleteTemplate: (id: string) =>
      authenticatedFetch(`${API}${buildTemplateUrlPath(id)}`, { method: "DELETE" }),
    deleteEmailTemplate: (name: string) =>
      authenticatedFetch(`${API}/email-templates/${encodeURIComponent(name)}`, { method: "DELETE" }),
    approveTemplate: (id: string) =>
      authenticatedFetch(`${API}${buildTemplateUrlPath(id, "/approve")}`, { method: "POST" }),
    retireTemplate: (id: string) =>
      authenticatedFetch(`${API}${buildTemplateUrlPath(id, "/retire")}`, { method: "POST" }),
  } as const;
}

export default function TemplatesIndex() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [emailTemplates, setEmailTemplates] = useState<EmailTemplate[]>([]);

  const api = useMemo(() => createTemplateConfigApi(), []);

  const loadTemplates = useMemo(
    () => () =>
      api
        .listTemplates()
        .then((r) => (r.ok ? r.json() : []))
        .then((data: any[]) =>
          setTemplates(
            data.length
              ? data
                  .filter((t) => !t.retired)
                  .map((t) => ({
                    id: t.id || t.name,
                    name: t.name,
                    docType: t.docType,
                    format: t.format || "--",
                    modified: t.modified || t.updated || "--",
                    approved: !!t.approved,
                    retired: !!t.retired,
                  }))
              : []
          )
        )
        .catch(() => setTemplates([])),
    [api],
  );

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    api
      .listEmailTemplates()
      .then((r) => (r.ok ? r.json() : []))
        .then((data: any[]) => {
        const sorted = Array.isArray(data)
          ? [...data].sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")))
          : [];
        setEmailTemplates(
          sorted.length
            ? sorted.map((t) => ({
                name: t.name,
                subject: t.subject,
                task: t.task,
              }))
            : []
        );
      })
        .catch(() => setEmailTemplates([]));
  }, [api]);

  const removeTemplate = async (id: string) => {
    setTemplates(templates.filter((t) => t.id !== id));
    try {
      await api.deleteTemplate(id);
    } catch {
      // ignore network errors in development mode
    }
  };

  const approveTemplate = async (id: string) => {
    try {
      const r = await api.approveTemplate(id);
      if (r.ok) {
        await loadTemplates();
        toast.success("Template approved.");
      } else {
        toast.error("Failed to approve template.");
      }
    } catch {
      toast.error("Failed to approve template.");
    }
  };

  const retireTemplate = async (id: string) => {
    try {
      const r = await api.retireTemplate(id);
      if (r.ok) {
        await loadTemplates();
        toast.success("Template retired.");
      } else {
        toast.error("Failed to retire template.");
      }
    } catch {
      toast.error("Failed to retire template.");
    }
  };

  const removeEmail = async (name: string) => {
    setEmailTemplates(emailTemplates.filter((t) => t.name !== name));
    try {
      await api.deleteEmailTemplate(name);
    } catch {
      // ignore network errors in development mode
    }
  };

    const handleDownload = (tpl: Template) => {
      window.open(`${API}${buildTemplateUrlPath(tpl.id, "/download")}`, "_blank");
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

      <Table caption="Templates" className="min-w-full text-sm">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Document Type</TableHead>
            <TableHead>Format</TableHead>
            <TableHead>Modified</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Actions</TableHead>
            <TableHead>Download</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {templates.map((t) => (
            <TableRow key={t.id} className="border-t last:border-none hover:bg-gray-50">
              <TableCell>{t.name}</TableCell>
              <TableCell>{t.docType || <span className="text-gray-400">--</span>}</TableCell>
              <TableCell>{t.format || <span className="text-gray-400">--</span>}</TableCell>
              <TableCell>{t.modified}</TableCell>
              <TableCell>{t.approved ? "Approved" : "Pending"}</TableCell>
              <TableCell className="w-32 space-x-1">
                {!t.approved && !t.retired && (
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Approve"
                    aria-label="Approve template"
                    onClick={() => approveTemplate(t.id)}
                  >
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  </Button>
                )}
                {t.approved && !t.retired && (
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Retire"
                    aria-label="Retire template"
                    onClick={() => retireTemplate(t.id)}
                  >
                    <Archive className="w-4 h-4 text-amber-600" />
                  </Button>
                )}
              </TableCell>
              <TableCell className="w-14">
                <Button
                  variant="ghost"
                  size="icon"
                  title="View or Download"
                  aria-label="View or Download"
                  onClick={() => handleDownload(t)}
                >
                  {t.format && ["DOCX", "HTML", "XML", "JSON", "TXT"].includes(t.format)
                    ? <Download className="w-4 h-4" />
                    : <Eye className="w-4 h-4" />}
                </Button>
              </TableCell>
              <TableCell className="w-14">
                <Button variant="ghost" size="icon" asChild>
                  <Link
                    href={`/configuration/templates/edit?id=${t.id}`}
                    title="Edit"
                    aria-label="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </Link>
                </Button>
              </TableCell>
              <TableCell className="w-14">
                <Button
                  variant="ghost"
                  size="icon"
                  title="Remove"
                  aria-label="Remove"
                  onClick={() => removeTemplate(t.id)}
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {templates.length === 0 && (
            <TableRow>
              <TableCell colSpan={9} className="text-center text-gray-400 py-10">
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
        <b>Tip:</b> Click "Create Template" to add Word, HTML, JSON, or XML templates for your team to use.
      </div>

      <div className="mt-12 flex flex-col sm:flex-row justify-between items-center gap-4">
        <h2 className="text-2xl font-bold">Email Templates</h2>
        <Button asChild className="bg-indigo-600 hover:bg-indigo-700 text-white">
          <Link href="/configuration/templates/new-email">+ New Email Template</Link>
        </Button>
      </div>

      <Table caption="Email templates" className="min-w-full text-sm mt-4">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Subject</TableHead>
            <TableHead>Task</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {emailTemplates.map((t) => (
            <TableRow key={t.name} className="border-t last:border-none hover:bg-gray-50">
              <TableCell>{t.name}</TableCell>
              <TableCell>{t.subject}</TableCell>
              <TableCell>{t.task || <span className="text-gray-400">--</span>}</TableCell>
              <TableCell className="w-14">
                <Button variant="ghost" size="icon" asChild>
                  <Link
                    href={`/configuration/templates/edit-email?id=${t.name}`}
                    title="Edit"
                    aria-label="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </Link>
                </Button>
              </TableCell>
              <TableCell className="w-14">
                <Button
                  variant="ghost"
                  size="icon"
                  title="Remove"
                  aria-label="Remove"
                  onClick={() => removeEmail(t.name)}
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {emailTemplates.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-10">
                No email templates found.<br />
                <Button asChild className="mt-4 bg-indigo-600 hover:bg-indigo-700 text-white">
                  <Link href="/configuration/templates/new-email">+ Add your first email template</Link>
                </Button>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <div className="mt-4 text-xs text-gray-500">
        Email templates are used for notifications throughout DocReview360.
        Use variables like {"{reviewer}"} or {"{document_title}"} when composing messages.
      </div>
    </div>
  );
}
