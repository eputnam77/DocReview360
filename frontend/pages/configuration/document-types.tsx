import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { API } from "@/lib/api";
import { Pencil, Trash } from "lucide-react";
import { useEffect, useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface DocType {
  id: string;
  name: string;
  phases?: string[];
  template?: string;
}

const DEFAULT_TYPES: DocType[] = [
  { id: "Advisory Circular", name: "Advisory Circular" },
  { id: "Policy Statement", name: "Policy Statement" },
  { id: "Release Notes", name: "Release Notes" },
];

const normalizeDocTypes = (items: unknown): DocType[] => {
  if (!Array.isArray(items)) return [];
  const list: DocType[] = items
    .map((item) => {
      if (typeof item === "string") {
        return { id: item, name: item };
      }
      if (item && typeof item === "object") {
        const anyItem = item as { id?: unknown; name?: unknown; template?: unknown; phases?: unknown; workflow?: unknown };
        const name = typeof anyItem.name === "string" ? anyItem.name : String(anyItem.name ?? "");
        if (!name) return null;
        const id = typeof anyItem.id === "string" && anyItem.id ? anyItem.id : name;
        const phases = Array.isArray(anyItem.phases)
          ? (anyItem.phases as string[])
          : Array.isArray(anyItem.workflow)
          ? (anyItem.workflow as string[])
          : undefined;
        const template = typeof anyItem.template === "string" ? anyItem.template : undefined;
        return { id, name, phases, template };
      }
      return null;
    })
    .filter((v): v is DocType => Boolean(v));
  return list.length ? list : [];
};

// Default phases that ship with the product
const DEFAULT_PHASES = [
  "Beta Documentation Review",
  "Draft Development",
  "Final Issuance",
  "General Availability",
  "Internal Coordination",
  "Maintenance / Revision Cycle",
  "Peer Review",
  "Public Comment / Proposed Rulemaking",
  "Release Candidate Review",
];

export default function DocumentTypesPage() {
  const [types, setTypes] = useState<DocType[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [phases, setPhases] = useState<string[]>([]);
  const [docTypePhaseMap, setDocTypePhaseMap] = useState<Record<string, string[]>>({});
  const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null);
  const [replacementDocType, setReplacementDocType] = useState<string>("");
  const [usageInfo, setUsageInfo] = useState<any>(null);

  useEffect(() => {
    // Load existing mappings from localStorage
    const saved = localStorage.getItem("docTypePhaseMap");
    if (saved) {
      try {
        setDocTypePhaseMap(JSON.parse(saved));
      } catch {
        // ignore invalid JSON
      }
    }

    // Fetch document types
    fetch(`${API}/document-types`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => {
        const list = normalizeDocTypes(data);
        setTypes(list.length ? list : DEFAULT_TYPES);
      })
      .catch(() => setTypes(DEFAULT_TYPES));

    // Fetch phases
    fetch(`${API}/phases`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: string[]) => setPhases(data.length ? data : DEFAULT_PHASES))
      .catch(() => setPhases(DEFAULT_PHASES));
  }, []);

  const addType = async () => {
    if (!newName.trim()) return;
    const body = {
      name: newName.trim(),
      template: `<h1>${newName.trim()}</h1>`,
      workflow: []
    };
    try {
      const r = await fetch(`${API}/document-types`, {
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

  const checkUsage = async (docTypeName: string) => {
    try {
      const response = await fetch(`${API}/document-types/${encodeURIComponent(docTypeName)}/usage`);
      if (response.ok) {
        const usage = await response.json();
        setUsageInfo(usage);
        return usage;
      }
    } catch (error) {
      console.error("Error checking usage:", error);
    }
    return null;
  };

  const removeType = async (id: string) => {
    // Check if document type is in use
    const usage = await checkUsage(id);
    
    if (usage && usage.in_use) {
      // Show delete dialog with replacement selection
      setShowDeleteDialog(id);
      return;
    }
    
    // If not in use, delete directly
    setTypes(types.filter((t) => t.id !== id));
    try {
      await fetch(`${API}/document-types/${encodeURIComponent(id)}`, { method: "DELETE" });
    } catch {
      // ignore network errors in development mode
    }
  };

  const confirmDelete = async () => {
    if (!showDeleteDialog || !replacementDocType) return;
    
    try {
      const response = await fetch(`${API}/document-types/${encodeURIComponent(showDeleteDialog)}?replacement=${encodeURIComponent(replacementDocType)}`, { 
        method: "DELETE" 
      });
      
      if (response.ok) {
        setTypes(types.filter((t) => t.id !== showDeleteDialog));
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error("Error deleting document type:", error);
      alert("Error deleting document type");
    }
    
    setShowDeleteDialog(null);
    setReplacementDocType("");
    setUsageInfo(null);
  };

  const cancelDelete = () => {
    setShowDeleteDialog(null);
    setReplacementDocType("");
    setUsageInfo(null);
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
      await fetch(`${API}/document-types/${id}`, {
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

  const changePhase = (docTypeId: string, phase: string) => {
    const currentPhases = docTypePhaseMap[docTypeId] || [];
    let updatedPhases: string[];

    if (currentPhases.includes(phase)) {
      // Remove phase if already selected
      updatedPhases = currentPhases.filter(p => p !== phase);
    } else {
      // Add phase if not selected
      updatedPhases = [...currentPhases, phase];
    }

    const updated = { ...docTypePhaseMap, [docTypeId]: updatedPhases };
    setDocTypePhaseMap(updated);
    localStorage.setItem("docTypePhaseMap", JSON.stringify(updated));
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
            <TableHead>Attached Phase</TableHead>
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
                <div className="flex flex-wrap gap-1">
                  {phases.map((p) => {
                    const currentPhases = docTypePhaseMap[t.id] || [];
                    const isSelected = currentPhases.includes(p);
                    return (
                      <label
                        key={p}
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs cursor-pointer border ${
                          isSelected
                            ? "bg-blue-100 text-blue-700 border-blue-300"
                            : "bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => changePhase(t.id, p)}
                          className="mr-1"
                        />
                        {p}
                      </label>
                    );
                  })}
                </div>
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

      {/* Delete Confirmation Dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Delete Document Type</h3>
            
            {usageInfo && (
              <div className="mb-4">
                <p className="text-red-600 mb-2">
                  This document type is currently in use by {usageInfo.usage_count} item(s):
                </p>
                {usageInfo.projects && usageInfo.projects.length > 0 && (
                  <div className="mb-2">
                    <p className="font-medium">Projects:</p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {usageInfo.projects.map((project: any) => (
                        <li key={project.id}>{project.name}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            <p className="mb-4">
              Please select a replacement document type to assign to all affected projects:
            </p>
            
            <Select value={replacementDocType} onValueChange={setReplacementDocType}>
              <SelectTrigger>
                <SelectValue placeholder="Select replacement document type" />
              </SelectTrigger>
              <SelectContent>
                {types
                  .filter(t => t.id !== showDeleteDialog)
                  .map((type) => (
                    <SelectItem key={type.id} value={type.id}>
                      {type.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            
            <div className="flex gap-2 mt-6">
              <Button 
                onClick={confirmDelete} 
                disabled={!replacementDocType}
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
