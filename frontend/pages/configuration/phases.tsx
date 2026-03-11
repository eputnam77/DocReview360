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
import { authenticatedFetch } from "@/lib/api";

interface Phase {
  id: string;
  name: string;
  workflowTemplateId?: string;
}

interface WorkflowTemplate {
  id: string;
  name?: string;
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

const NONE_WORKFLOW_VALUE = "__none__";

function normalizePhases(items: unknown): Phase[] {
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => {
      if (typeof item === "string") {
        const trimmed = item.trim();
        return trimmed ? { id: trimmed, name: trimmed } : null;
      }
      if (item && typeof item === "object") {
        const value = item as {
          id?: unknown;
          name?: unknown;
          workflow_template_id?: unknown;
          workflowTemplateId?: unknown;
        };
        const name =
          typeof value.name === "string" && value.name.trim()
            ? value.name.trim()
            : "";
        if (!name) return null;
        const id =
          typeof value.id === "string" && value.id.trim() ? value.id.trim() : name;
        const workflowTemplateId =
          typeof value.workflow_template_id === "string" && value.workflow_template_id.trim()
            ? value.workflow_template_id.trim()
            : typeof value.workflowTemplateId === "string" && value.workflowTemplateId.trim()
              ? value.workflowTemplateId.trim()
              : undefined;
        return { id, name, workflowTemplateId };
      }
      return null;
    })
    .filter(Boolean) as Phase[];
}

export default function PhasesPage() {
  const [phases, setPhases] = useState<Phase[]>([]);
  const [workflowTemplates, setWorkflowTemplates] = useState<WorkflowTemplate[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null);
  const [replacementPhase, setReplacementPhase] = useState<string>("");
  const [usageInfo, setUsageInfo] = useState<UsageInfo | null>(null);

  const loadPhases = async () => {
    try {
      const configRes = await authenticatedFetch('/phases/config');
      if (configRes.ok) {
        const data = await configRes.json();
        const normalized = normalizePhases(data);
        if (normalized.length > 0) {
          setPhases(normalized);
          return;
        }
      }
    } catch {
      // fallback below
    }

    try {
      const res = await authenticatedFetch('/phases');
      if (!res.ok) {
        setPhases([]);
        return;
      }
      const data = await res.json();
      setPhases(normalizePhases(data));
    } catch {
      setPhases([]);
    }
  };

  const loadWorkflowTemplates = async () => {
    try {
      const res = await authenticatedFetch('/workflow-templates');
      if (!res.ok) {
        setWorkflowTemplates([]);
        return;
      }
      const data = await res.json();
      if (!Array.isArray(data)) {
        setWorkflowTemplates([]);
        return;
      }
      const items: WorkflowTemplate[] = data
        .map((item) => {
          if (!item || typeof item !== "object") return null;
          const value = item as { id?: unknown; name?: unknown };
          const id = typeof value.id === "string" ? value.id : "";
          if (!id) return null;
          const name = typeof value.name === "string" ? value.name : undefined;
          return { id, name };
        })
        .filter(Boolean) as WorkflowTemplate[];
      setWorkflowTemplates(items);
    } catch {
      setWorkflowTemplates([]);
    }
  };

  useEffect(() => {
    void loadPhases();
    void loadWorkflowTemplates();
  }, []);

  const checkUsage = async (phaseName: string): Promise<UsageInfo | null> => {
    try {
      const response = await authenticatedFetch(`/phases/${encodeURIComponent(phaseName)}/usage`);
      if (!response.ok) return null;
      const usage = (await response.json()) as UsageInfo;
      setUsageInfo(usage);
      return usage;
    } catch {
      return null;
    }
  };

  const addPhase = async () => {
    const trimmed = newName.trim();
    if (!trimmed) return;

    try {
      const r = await authenticatedFetch('/phases', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!r.ok) {
        toast.error("Failed to add phase");
        return;
      }
      await loadPhases();
      setNewName("");
    } catch {
      toast.error("Failed to add phase");
    }
  };

  const savePhaseWorkflowTemplate = async (phaseName: string, templateId: string) => {
    const workflowTemplateId = templateId === NONE_WORKFLOW_VALUE ? null : templateId;

    try {
      const res = await authenticatedFetch(
        `/phases/${encodeURIComponent(phaseName)}/workflow-template`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ workflow_template_id: workflowTemplateId }),
        },
      );

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        const detail =
          typeof payload?.detail === "string" && payload.detail.trim()
            ? payload.detail
            : "Failed to update phase workflow";
        toast.error(detail);
        return;
      }

      const updated = (await res.json()) as {
        name?: string;
        workflow_template_id?: string | null;
      };

      setPhases((prev) =>
        prev.map((phase) =>
          phase.name === phaseName
            ? {
                ...phase,
                workflowTemplateId:
                  typeof updated.workflow_template_id === "string"
                    ? updated.workflow_template_id
                    : undefined,
              }
            : phase,
        ),
      );
    } catch {
      toast.error("Failed to update phase workflow");
    }
  };

  const removePhase = async (id: string) => {
    const usage = await checkUsage(id);

    if (usage && usage.in_use) {
      setShowDeleteDialog(id);
      return;
    }

    try {
      const res = await authenticatedFetch(`/phases/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (res.ok) {
        setPhases(phases.filter((p) => p.id !== id));
      } else {
        toast.error("Failed to delete phase");
      }
    } catch {
      toast.error("Failed to delete phase");
    }
  };

  const confirmDelete = async () => {
    if (!showDeleteDialog || !replacementPhase) return;

    try {
      const response = await authenticatedFetch(
        `/phases/${encodeURIComponent(showDeleteDialog)}?replacement=${encodeURIComponent(replacementPhase)}`,
        {
          method: "DELETE",
        },
      );

      if (response.ok) {
        setPhases(phases.filter((p) => p.id !== showDeleteDialog));
      } else {
        const error = await response.json();
        toast.error(`Error: ${String(error?.detail ?? "Failed to delete phase")}`);
      }
    } catch {
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
    const trimmed = editName.trim();
    if (!trimmed) return;

    try {
      const res = await authenticatedFetch(`/phases/${encodeURIComponent(id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!res.ok) {
        throw new Error("Failed to update phase");
      }

      setPhases(
        phases.map((p) =>
          p.id === id
            ? {
                ...p,
                id: trimmed,
                name: trimmed,
              }
            : p,
        ),
      );
      setEditingId(null);
      setEditName("");
    } catch {
      toast.error("Failed to update phase");
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
  };

  return (
    <div className="space-y-6 p-8">
      <h1 className="text-2xl font-bold">Phases</h1>
      <form
        className="flex items-end gap-2"
        onSubmit={(e: FormEvent<HTMLFormElement>) => {
          e.preventDefault();
          void addPhase();
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
            <TableHead>Default Workflow</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {phases.map((p: Phase) => (
            <TableRow key={p.id}>
              <TableCell className="min-w-[180px]">
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
              <TableCell className="min-w-[240px]">
                <Select
                  value={p.workflowTemplateId || NONE_WORKFLOW_VALUE}
                  onValueChange={(value) => void savePhaseWorkflowTemplate(p.name, value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select default workflow" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE_WORKFLOW_VALUE}>No default workflow</SelectItem>
                    {workflowTemplates.map((template) => (
                      <SelectItem key={template.id} value={template.id}>
                        {template.name || template.id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableCell>
              <TableCell className="w-28">
                {editingId === p.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => void saveEdit(p.id)}>
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
                    <Pencil className="h-4 w-4" />
                  </Button>
                )}
              </TableCell>
              <TableCell className="w-20">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => void removePhase(p.id)}
                  title="Remove"
                  aria-label="Remove"
                >
                  <Trash className="h-4 w-4 text-red-600" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {phases.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="py-6 text-center text-gray-400">
                No phases defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {showDeleteDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="mx-4 w-full max-w-md rounded-lg bg-white p-6">
            <h3 className="mb-4 text-lg font-semibold">Delete Phase</h3>

            {usageInfo && (
              <div className="mb-4">
                <p className="mb-2 text-red-600">
                  This phase is currently in use by {usageInfo.usage_count} item(s):
                </p>
                {usageInfo.projects && usageInfo.projects.length > 0 && (
                  <div className="mb-2">
                    <p className="font-medium">Projects:</p>
                    <ul className="list-inside list-disc text-sm text-gray-600">
                      {usageInfo.projects.map((project) => (
                        <li key={project.id}>{project.name}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {usageInfo.workflows && usageInfo.workflows.length > 0 && (
                  <div className="mb-2">
                    <p className="font-medium">Workflows:</p>
                    <ul className="list-inside list-disc text-sm text-gray-600">
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

            <div className="mt-6 flex gap-2">
              <Button onClick={() => void confirmDelete()} disabled={!replacementPhase} variant="danger">
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
