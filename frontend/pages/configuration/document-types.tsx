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

interface DocType {
  id: string;
  name: string;
  workflow?: string[];
  template?: string;
}

const DEMO_TYPES: DocType[] = [
  { id: "dt1", name: "Advisory Circular" },
  { id: "dt2", name: "Policy Statement" },
  { id: "dt3", name: "Release Notes" },
];

export default function DocumentTypesPage() {
  const [types, setTypes] = useState<DocType[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");

  useEffect(() => {
    fetch("/api/document-types")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setTypes(
          data.length
            ? data.map((d) => ({
                id: d.name,
                name: d.name,
                template: d.template,
                workflow: d.workflow,
              }))
            : DEMO_TYPES
        )
      )
      .catch(() => setTypes(DEMO_TYPES));
  }, []);

  const addType = async () => {
    if (!newName.trim()) return;
    const body = { name: newName.trim() };
    try {
      const r = await fetch("/api/document-types", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        const created = await r.json();
        setTypes([...types, { id: created.name, name: created.name }]);
      }
    } catch {
      setTypes([
        ...types,
        { id: "dt-" + Date.now().toString(), name: body.name },
      ]);
    }
    setNewName("");
  };

  const removeType = async (id: string) => {
    setTypes(types.filter((t) => t.id !== id));
    try {
      await fetch(`/api/document-types/${id}`, { method: "DELETE" });
    } catch {
      // ignore network errors in demo mode
    }
  };

  const startEdit = (t: DocType) => {
    setEditingId(t.id);
    setEditName(t.name);
  };

  const saveEdit = async (id: string) => {
    if (!editName.trim()) return;
    const body = { name: editName.trim() };
    setTypes(types.map((t) => (t.id === id ? { ...t, name: body.name } : t)));
    try {
      await fetch(`/api/document-types/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch {
      // ignore network errors in demo mode
    }
    setEditingId(null);
    setEditName("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Document Types</h1>
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          addType();
        }}
      >
        <Input
          placeholder="New Document Type"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="max-w-xs"
        />
        <Button type="submit" size="sm">
          Add
        </Button>
      </form>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Document Type</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
            <TableHead>Attached Workflow</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {types.map((t) => (
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
                  onClick={() => removeType(t.id)}
                  title="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
              <TableCell>
                {t.workflow && t.workflow.length
                  ? t.workflow.join(", ")
                  : <span className="text-gray-400">—</span>}
              </TableCell>
            </TableRow>
          ))}
          {types.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No document types defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
