import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, } from "@/components/ui/table";
import { Pencil, Trash } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
export default function PhasesPage() {
    const [phases, setPhases] = useState([]);
    const [newName, setNewName] = useState("");
    const [editingId, setEditingId] = useState(null);
    const [editName, setEditName] = useState("");
    const [showDeleteDialog, setShowDeleteDialog] = useState(null);
    const [replacementPhase, setReplacementPhase] = useState("");
    const [usageInfo, setUsageInfo] = useState(null);
    useEffect(() => {
        const normalizePhases = (items) => {
            if (!Array.isArray(items))
                return [];
            const list = items
                .map((item) => {
                if (typeof item === "string") {
                    return { id: item, name: item };
                }
                if (item && typeof item === "object") {
                    const anyItem = item;
                    const name = typeof anyItem.name === "string"
                        ? anyItem.name
                        : String(anyItem.name ?? "");
                    const id = typeof anyItem.id === "string" && anyItem.id
                        ? anyItem.id
                        : name;
                    if (name)
                        return { id, name };
                }
                return null;
            })
                .filter(Boolean);
            return list.length ? list : [];
        };
        (async () => {
            try {
                const r = await fetch("/api/phases");
                if (r.ok) {
                    const data = await r.json();
                    setPhases(normalizePhases(data));
                }
                else {
                    setPhases([]);
                }
            }
            catch {
                setPhases([]);
            }
        })();
    }, []);
    const checkUsage = async (phaseName) => {
        try {
            const response = await fetch(`/api/phases/${encodeURIComponent(phaseName)}/usage`);
            if (response.ok) {
                const usage = (await response.json());
                setUsageInfo(usage);
                return usage;
            }
        }
        catch (error) {
            console.error("Error checking usage:", error);
        }
        return null;
    };
    const addPhase = async () => {
        if (!newName.trim())
            return;
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
                const normalize = (items) => {
                    if (!Array.isArray(items))
                        return phases;
                    const list = items
                        .map((item) => typeof item === "string"
                        ? { id: item, name: item }
                        : item && typeof item === "object"
                            ? {
                                id: typeof item.id === "string"
                                    ? item.id
                                    : item.name ?? "",
                                name: item.name ?? "",
                            }
                            : null)
                        .filter(Boolean);
                    return list.length ? list : phases;
                };
                setPhases(normalize(data));
            }
            else {
                toast.error("Failed to add phase");
            }
        }
        catch {
            toast.error("Failed to add phase");
        }
        setNewName("");
    };
    const removePhase = async (id) => {
        // Check if phase is in use
        const usage = await checkUsage(id);
        if (usage && usage.in_use) {
            // Show delete dialog with replacement selection
            setShowDeleteDialog(id);
            return;
        }
        // If not in use, delete directly
        try {
            const res = await fetch(`/api/phases/${encodeURIComponent(id)}`, { method: "DELETE" });
            if (res.ok) {
                setPhases(phases.filter((p) => p.id !== id));
            }
            else {
                toast.error("Failed to delete phase");
            }
        }
        catch {
            toast.error("Failed to delete phase");
        }
    };
    const confirmDelete = async () => {
        if (!showDeleteDialog || !replacementPhase)
            return;
        try {
            const response = await fetch(`/api/phases/${encodeURIComponent(showDeleteDialog)}?replacement=${encodeURIComponent(replacementPhase)}`, {
                method: "DELETE",
            });
            if (response.ok) {
                setPhases(phases.filter((p) => p.id !== showDeleteDialog));
            }
            else {
                const error = await response.json();
                toast.error(`Error: ${error.detail}`);
            }
        }
        catch (error) {
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
    const startEdit = (p) => {
        setEditingId(p.id);
        setEditName(p.name);
    };
    const saveEdit = async (id) => {
        if (!editName.trim())
            return;
        const body = { name: editName.trim() };
        try {
            const res = await fetch(`/api/phases/${encodeURIComponent(id)}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                throw new Error("Failed to update phase");
            }
            setPhases(phases.map((p) => (p.id === id ? { ...p, name: body.name } : p)));
            setEditingId(null);
            setEditName("");
            return;
        }
        catch {
            toast.error("Failed to update phase");
        }
    };
    const cancelEdit = () => {
        setEditingId(null);
        setEditName("");
    };
    return (<div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Phases</h1>
      <form className="flex items-end gap-2" onSubmit={(e) => {
            e.preventDefault();
            addPhase();
        }}>
        <Input placeholder="New Phase" value={newName} onChange={(e) => setNewName(e.target.value)} className="max-w-xs"/>
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
          </TableRow>
        </TableHeader>
        <TableBody>
          {phases.map((p) => (<TableRow key={p.id}>
              <TableCell className="min-w-[150px]">
                {editingId === p.id ? (<Input value={editName} onChange={(e) => setEditName(e.target.value)} className="h-8"/>) : (p.name)}
              </TableCell>
              <TableCell className="w-28">
                {editingId === p.id ? (<div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(p.id)}>
                      Save
                    </Button>
                    <Button size="sm" variant="ghost" onClick={cancelEdit}>
                      Cancel
                    </Button>
                  </div>) : (<Button variant="ghost" size="icon" onClick={() => startEdit(p)} title="Edit" aria-label="Edit">
                    <Pencil className="w-4 h-4"/>
                  </Button>)}
              </TableCell>
              <TableCell className="w-20">
                <Button variant="ghost" size="icon" onClick={() => removePhase(p.id)} title="Remove" aria-label="Remove">
                  <Trash className="w-4 h-4 text-red-600"/>
                </Button>
              </TableCell>
            </TableRow>))}
          {phases.length === 0 && (<TableRow>
              <TableCell colSpan={3} className="text-center text-gray-400 py-6">
                No phases defined.
              </TableCell>
            </TableRow>)}
        </TableBody>
      </Table>

      {/* Delete Confirmation Dialog */}
      {showDeleteDialog && (<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Delete Phase</h3>
            
            {usageInfo && (<div className="mb-4">
                <p className="text-red-600 mb-2">
                  This phase is currently in use by {usageInfo.usage_count} item(s):
                </p>
                {usageInfo.projects && usageInfo.projects.length > 0 && (<div className="mb-2">
                    <p className="font-medium">Projects:</p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {usageInfo.projects.map((project) => (<li key={project.id}>{project.name}</li>))}
                    </ul>
                  </div>)}
                {usageInfo.workflows && usageInfo.workflows.length > 0 && (<div className="mb-2">
                    <p className="font-medium">Workflows:</p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {usageInfo.workflows.map((workflow) => (<li key={workflow.id}>{workflow.project}</li>))}
                    </ul>
                  </div>)}
              </div>)}
            
            <p className="mb-4">
              Please select a replacement phase to assign to all affected items:
            </p>
            
            <Select value={replacementPhase} onValueChange={(v) => setReplacementPhase(v)}>
              <SelectTrigger>
                <SelectValue placeholder="Select replacement phase"/>
              </SelectTrigger>
              <SelectContent>
                {phases
                .filter((p) => p.id !== showDeleteDialog)
                .map((phase) => (<SelectItem key={phase.id} value={phase.id}>
                      {phase.name}
                    </SelectItem>))}
              </SelectContent>
            </Select>
            
            <div className="flex gap-2 mt-6">
              <Button onClick={confirmDelete} disabled={!replacementPhase} variant="danger">
                Delete and Replace
              </Button>
              <Button onClick={cancelDelete} variant="outline">
                Cancel
              </Button>
            </div>
          </div>
        </div>)}
    </div>);
}
