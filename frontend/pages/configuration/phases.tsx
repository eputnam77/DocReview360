import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Pencil, Trash } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "react-hot-toast";

interface Phase {
  id: string;
  name: string;
}

interface UsageProject {
  id: string | number;
  name: string;
}

interface UsageWorkflow {
  id: string | number;
  project: string;
}

interface UsageInfo {
  in_use: boolean;
  usage_count: number;
  projects?: UsageProject[];
  workflows?: UsageWorkflow[];
}

export default function PhasesPage() {
  const [phases, setPhases] = useState<Phase[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [workflows, setWorkflows] = useState<string[]>([]);
  const [phaseMap, setPhaseMap] = useState<Record<string, string>>({});
  const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null);
  const [replacementPhase, setReplacementPhase] = useState<string>("");
  const [usageInfo, setUsageInfo] = useState<UsageInfo | null>(null);

  useEffect(() => {
    // Load existing mappings from localStorage
    const saved = localStorage.getItem("phaseWorkflowMap");
    if (saved) {
      try {
        setPhaseMap(JSON.parse(saved));
      } catch {
        // ignore invalid JSON
      }
    }

    const normalizePhases = (items: unknown): Phase[] => {
      if (!Array.isArray(items)) return [];
      const list: Phase[] = items
        .map((item) => {
          if (typeof item === "string") {
            return { id: item, name: item };
          }
          if (item && typeof item === "object") {
            const anyItem = item as { id?: unknown; name?: unknown };
            const name =
              typeof anyItem.name === "string"
                ? anyItem.name
                : String(anyItem.name ?? "");
            const id =
              typeof anyItem.id === "string" && anyItem.id
                ? anyItem.id
                : name;
            if (name) return { id, name };
          }
          return null;
        })
        .filter(Boolean) as Phase[];
      return list.length ? list : [];
    };

    const normalizeWorkflows = (items: unknown): string[] => {
      if (!Array.isArray(items)) return [];
      const names = items
        .map((wf) =>
          typeof wf === "string"
            ? wf
            : wf && typeof wf === "object" && "name" in wf
            ? String((wf as { name?: unknown }).name ?? "")
            : null,
        )
        .filter((v): v is string => Boolean(v));
      return names.length ? names : [];
    };

    (async () => {
      try {
        const r = await fetch("/api/phases");
        if (r.ok) {
          const data = await r.json();
          setPhases(normalizePhases(data));
        } else {
          setPhases([]);
        }
      } catch {
        setPhases([]);
      }

      try {
        const r = await fetch("/api/workflow-templates");
        if (r.ok) {
          const data = await r.json();
          setWorkflows(normalizeWorkflows(data));
        } else {
          setWorkflows([]);
        }
      } catch {
        setWorkflows([]);
      }
    })();
  }, []);

  const checkUsage = async (phaseName: string): Promise<UsageInfo | null> => {
    try {
      const response = await fetch(
        `/api/phases/${encodeURIComponent(phaseName)}/usage`,
      );
      if (response.ok) {
        const usage = (await response.json()) as UsageInfo;
        setUsageInfo(usage);
        return usage;
      }
    } catch (error) {
      console.error("Error checking usage:", error);
    }
    return null;
  };

  const addPhase = async () => {
    if (!newName.trim()) return;
    const body = { name: newName.trim() };
    try {
      const r = await fetch("/api/phases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        const data = await r.json();
        // Normalize whether API returns strings or objects
        const normalize = (items: unknown): Phase[] => {
          if (!Array.isArray(items)) return phases;
          const list: Phase[] = items
            .map((item) =>
              typeof item === "string"
                ? { id: item, name: item }
                : item && typeof item === "object"
                ? {
                    id:
                      typeof (item as { id?: unknown }).id === "string"
                        ? ((item as { id?: string }).id as string)
                        : (item as { name?: string }).name ?? "",
                    name: (item as { name?: string }).name ?? "",
                  }
                : null,
            )
            .filter(Boolean) as Phase[];
          return list.length ? list : phases;
        };
        setPhases(normalize(data));
      } else {
        // Fallback when API route isn't present
        setPhases([...phases, { id: body.name, name: body.name }]);
      }
    } catch {
      // Network or other error: fallback to local optimistic add
      setPhases([...phases, { id: body.name, name: body.name }]);
    }
    setNewName("");
  };

  const removePhase = async (id: string) => {
    // Check if phase is in use
    const usage = await checkUsage(id);
    
    if (usage && usage.in_use) {
      // Show delete dialog with replacement selection
      setShowDeleteDialog(id);
      return;
    }
    
    // If not in use, delete directly
    setPhases(phases.filter((p) => p.id !== id));
    try {
      await fetch(`/api/phases/${encodeURIComponent(id)}`, { method: "DELETE" });
    } catch {
      // ignore network errors in development mode
    }
  };

  const confirmDelete = async () => {
    if (!showDeleteDialog || !replacementPhase) return;
    
    try {
      const response = await fetch(
        `/api/phases/${encodeURIComponent(showDeleteDialog)}?replacement=${encodeURIComponent(
          replacementPhase,
        )}`,
        {
          method: "DELETE",
        },
      );
      
      if (response.ok) {
        setPhases(phases.filter((p) => p.id !== showDeleteDialog));
      } else {
        const error = await response.json();
        toast.error(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error("Error deleting phase:", error);
      toast.error("Error deleting phase");
    }
    
    setShowDeleteDialog(null);
    setReplacementPhase("");
    setUsageInfo(null);
  };

  const cancelDelete = () => {
    setShowDeleteDialog(null);
    setReplacementPhase("");
    setUsageInfo(null);
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
      await fetch(`/api/phases/${encodeURIComponent(id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch {
      // ignore network errors in development mode
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
        onSubmit={(e: FormEvent<HTMLFormElement>) => {
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
      <Table caption="Phases">
        <TableHeader>
          <TableRow>
            <TableHead>Phase</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
            <TableHead>Attached Workflow</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {phases.map((p: Phase) => (
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
                    aria-label="Edit"
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
                  aria-label="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
              <TableCell>
                <Select
                  value={phaseMap[p.id] || ""}
                  onValueChange={(v: string) => changeWorkflow(p.id, v)}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {workflows.map((w: string) => (
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

      {/* Delete Confirmation Dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Delete Phase</h3>
            
            {usageInfo && (
              <div className="mb-4">
                <p className="text-red-600 mb-2">
                  This phase is currently in use by {usageInfo.usage_count} item(s):
                </p>
                {usageInfo.projects && usageInfo.projects.length > 0 && (
                  <div className="mb-2">
                    <p className="font-medium">Projects:</p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {usageInfo.projects.map((project) => (
                        <li key={project.id}>{project.name}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {usageInfo.workflows && usageInfo.workflows.length > 0 && (
                  <div className="mb-2">
                    <p className="font-medium">Workflows:</p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {usageInfo.workflows.map((workflow) => (
                        <li key={workflow.id}>{workflow.project}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            <p className="mb-4">
              Please select a replacement phase to assign to all affected items:
            </p>
            
            <Select value={replacementPhase} onValueChange={(v: string) => setReplacementPhase(v)}>
              <SelectTrigger>
                <SelectValue placeholder="Select replacement phase" />
              </SelectTrigger>
              <SelectContent>
                {phases
                  .filter((p: Phase) => p.id !== showDeleteDialog)
                  .map((phase: Phase) => (
                    <SelectItem key={phase.id} value={phase.id}>
                      {phase.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            
            <div className="flex gap-2 mt-6">
              <Button 
                onClick={confirmDelete} 
                disabled={!replacementPhase}
                variant="danger"
              >
                Delete and Replace
              </Button>
              <Button onClick={cancelDelete} variant="outline">
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
