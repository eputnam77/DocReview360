import React, { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Pencil, Trash } from "lucide-react";

interface Template {
  id: string;
  name: string;
  docType?: string;
}

const DEMO_TEMPLATES: Template[] = [
  { id: "tpl1", name: "AC Template", docType: "Advisory Circular" },
  { id: "tpl2", name: "Release Notes", docType: "Release Notes" },
];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [newName, setNewName] = useState("");
  const [newDocType, setNewDocType] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDocType, setEditDocType] = useState("");

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
              }))
            : DEMO_TEMPLATES,
        )
      )
      .catch(() => setTemplates(DEMO_TEMPLATES));
  }, []);

  const addTemplate = () => {
    if (!newName.trim()) return;
    setTemplates([
      ...templates,
      {
        id: "tpl-" + Date.now().toString(),
        name: newName.trim(),
        docType: newDocType.trim() || undefined,
      },
    ]);
    setNewName("");
    setNewDocType("");
  };

  const removeTemplate = (id: string) =>
    setTemplates(templates.filter((t) => t.id !== id));

  const startEdit = (t: Template) => {
    setEditingId(t.id);
    setEditName(t.name);
    setEditDocType(t.docType || "");
  };

  const saveEdit = (id: string) => {
    if (!editName.trim()) return;
    setTemplates(
      templates.map((t) =>
        t.id === id
          ? { ...t, name: editName.trim(), docType: editDocType.trim() || undefined }
          : t,
      ),
    );
    setEditingId(null);
    setEditName("");
    setEditDocType("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditDocType("");
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Templates</h1>
      <form
        className="flex flex-wrap gap-2 items-end"
        onSubmit={(e) => {
          e.preventDefault();
          addTemplate();
        }}
      >
        <Input
          placeholder="Template Name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="max-w-xs"
        />
        <Input
          placeholder="Document Type"
          value={newDocType}
          onChange={(e) => setNewDocType(e.target.value)}
          className="max-w-xs"
        />
        <Button type="submit" size="sm">
          Add
        </Button>
      </form>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Template</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
            <TableHead>Document Type</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {templates.map((t) => (
            <TableRow key={t.id}>
              <TableCell className="min-w-[150px]">
                {editingId === t.id ? (
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="h-8"
                  />
                ) : (
                  t.name
                )}
              </TableCell>
              <TableCell className="w-28">
                {editingId === t.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(t.id)}>
                      Save
                    </Button>
                    <Button size="sm" variant="ghost" onClick={cancelEdit}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => startEdit(t)}
                    title="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </Button>
                )}
              </TableCell>
              <TableCell className="w-20">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeTemplate(t.id)}
                  title="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
              <TableCell>
                {editingId === t.id ? (
                  <Input
                    value={editDocType}
                    onChange={(e) => setEditDocType(e.target.value)}
                    className="h-8"
                  />
                ) : (
                  t.docType || <span className="text-gray-400">—</span>
                )}
              </TableCell>
            </TableRow>
          ))}
          {templates.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No templates defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
