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

interface Phase {
  id: string;
  name: string;
  workflow?: string[];
}

const DEMO_PHASES: Phase[] = [
  { id: "phase-faa", name: "FAA Review" },
  { id: "phase-comment", name: "Public Comment" },
  { id: "phase-final", name: "Final Issuance" },
];

export default function PhasesPage() {
  const [phases, setPhases] = useState<Phase[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");

  useEffect(() => {
    fetch("/api/phases")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setPhases(
          data.length
            ? data.map((d) => ({
                id: d.name,
                name: d.name,
                workflow: d.workflow,
              }))
            : DEMO_PHASES,
        )
      )
      .catch(() => setPhases(DEMO_PHASES));
  }, []);

  const addPhase = () => {
    if (!newName.trim()) return;
    setPhases([
      ...phases,
      { id: "ph-" + Date.now().toString(), name: newName.trim() },
    ]);
    setNewName("");
  };

  const removePhase = (id: string) =>
    setPhases(phases.filter((p) => p.id !== id));

  const startEdit = (p: Phase) => {
    setEditingId(p.id);
    setEditName(p.name);
  };

  const saveEdit = (id: string) => {
    if (!editName.trim()) return;
    setPhases(
      phases.map((p) => (p.id === id ? { ...p, name: editName.trim() } : p)),
    );
    setEditingId(null);
    setEditName("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Phases</h1>
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          addPhase();
        }}
      >
        <Input
          placeholder="New Phase"
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
            <TableHead>Phase</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
            <TableHead>Attached Workflow</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {phases.map((p) => (
            <TableRow key={p.id}>
              <TableCell className="min-w-[150px]">
                {editingId === p.id ? (
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="h-8"
                  />
                ) : (
                  p.name
                )}
              </TableCell>
              <TableCell className="w-28">
                {editingId === p.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(p.id)}>
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
                    onClick={() => startEdit(p)}
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
                  onClick={() => removePhase(p.id)}
                  title="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
              <TableCell>
                {p.workflow && p.workflow.length ? (
                  p.workflow.join(", ")
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </TableCell>
            </TableRow>
          ))}
          {phases.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No phases defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
