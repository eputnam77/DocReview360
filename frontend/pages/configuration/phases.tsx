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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { API } from "@/lib/api";

interface Phase {
  id: string;
  name: string;
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
  const [workflows, setWorkflows] = useState<string[]>([]);
  const [phaseMap, setPhaseMap] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch(`${API}/phases`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setPhases(
          data.length
            ? data.map((d) => ({
                id: d.name,
                name: d.name,
              }))
            : DEMO_PHASES,
        )
      )
      .catch(() => setPhases(DEMO_PHASES));
    fetch(`${API}/workflows`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => setWorkflows(data.map((w) => w.name)))
      .catch(() => setWorkflows([]));
    const saved = localStorage.getItem("phaseWorkflowMap");
    if (saved) {
      try {
        setPhaseMap(JSON.parse(saved));
      } catch {
        // ignore
      }
    }
  }, []);

  const addPhase = async () => {
    if (!newName.trim()) return;
    const body = { name: newName.trim() };
    try {
      const r = await fetch(`${API}/phases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        const created = await r.json();
        setPhases([...phases, { id: created.name, name: created.name }]);
      }
    } catch {
      setPhases([
        ...phases,
        { id: "ph-" + Date.now().toString(), name: body.name },
      ]);
    }
    setNewName("");
  };

  const removePhase = async (id: string) => {
    setPhases(phases.filter((p) => p.id !== id));
    try {
      await fetch(`${API}/phases/${id}`, { method: "DELETE" });
    } catch {
      // ignore network errors in demo mode
    }
  };

  const startEdit = (p: Phase) => {
    setEditingId(p.id);
    setEditName(p.name);
  };

  const saveEdit = async (id: string) => {
    if (!editName.trim()) return;
    const body = { name: editName.trim() };
    setPhases(phases.map((p) => (p.id === id ? { ...p, name: body.name } : p)));
    try {
      await fetch(`${API}/phases/${id}`, {
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

  const changeWorkflow = (phaseId: string, wf: string) => {
    const updated = { ...phaseMap, [phaseId]: wf };
    setPhaseMap(updated);
    localStorage.setItem("phaseWorkflowMap", JSON.stringify(updated));
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
                <Select
                  value={phaseMap[p.id] || ""}
                  onValueChange={(v) => changeWorkflow(p.id, v)}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {workflows.map((w) => (
                      <SelectItem key={w} value={w}>
                        {w}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
