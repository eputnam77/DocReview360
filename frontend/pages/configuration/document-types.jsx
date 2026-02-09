import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, } from "@/components/ui/table";
import { Pencil, Plus, Trash } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "react-hot-toast";
const normalizeDocTypes = (items) => {
    if (!Array.isArray(items))
        return [];
    return items
        .map((item) => {
        if (!item || typeof item !== "object")
            return null;
        const anyItem = item;
        const name = typeof anyItem.name === "string" && anyItem.name.trim()
            ? anyItem.name.trim()
            : "";
        if (!name)
            return null;
        const id = typeof anyItem.id === "string" && anyItem.id.trim()
            ? anyItem.id.trim()
            : name;
        let phases;
        if (Array.isArray(anyItem.phases)) {
            phases = anyItem.phases.filter((p) => typeof p === "string" && p.trim());
        }
        else if (Array.isArray(anyItem.workflow)) {
            phases = anyItem.workflow.filter((p) => typeof p === "string" && p.trim());
        }
        const template = typeof anyItem.template === "string" && anyItem.template.trim()
            ? anyItem.template
            : undefined;
        return { id, name, phases, template };
    })
        .filter((v) => Boolean(v));
};
function PhaseSelector({ docTypeId, phases, selectedPhases, changePhase, }) {
    const [search, setSearch] = useState("");
    const filtered = phases.filter((p) => p.toLowerCase().includes(search.toLowerCase()));
    return (<div className="flex flex-wrap items-center gap-1">
      {selectedPhases.length > 0 ? (selectedPhases.map((p) => (<Badge key={p} variant="outline" className="whitespace-nowrap">
            {p}
          </Badge>))) : (<span className="text-gray-400 text-xs italic">No phases</span>)}
      <Popover>
        <PopoverTrigger as={Fragment}>
          <Button size="sm" variant="outline" className="h-6 px-2 text-xs gap-1">
            <Plus className="w-3 h-3"/>
            {selectedPhases.length ? "Edit" : "Add"}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-2">
          <Input placeholder="Search phases..." value={search} onChange={(e) => setSearch(e.target.value)} className="mb-2 h-8 text-xs"/>
          <ScrollArea className="max-h-48">
            <div className="space-y-1">
              {filtered.map((p) => {
            const isSelected = selectedPhases.includes(p);
            return (<label key={p} className="flex items-center space-x-2 cursor-pointer px-1 py-1 rounded hover:bg-gray-50">
                    <input type="checkbox" checked={isSelected} onChange={() => changePhase(docTypeId, p)} className="h-3 w-3"/>
                    <span className="text-sm">{p}</span>
                  </label>);
        })}
            </div>
          </ScrollArea>
        </PopoverContent>
      </Popover>
    </div>);
}
export default function DocumentTypesPage() {
    const [types, setTypes] = useState([]);
    const [newName, setNewName] = useState("");
    const [editingId, setEditingId] = useState(null);
    const [editName, setEditName] = useState("");
    const [phases, setPhases] = useState([]);
    const [showDeleteDialog, setShowDeleteDialog] = useState(null);
    const [replacementDocType, setReplacementDocType] = useState("");
    const [usageInfo, setUsageInfo] = useState(null);
    useEffect(() => {
        // Fetch document types from backend
        fetch("/api/document-types")
            .then((r) => (r.ok ? r.json() : []))
            .then((data) => {
            const list = normalizeDocTypes(data);
            setTypes(list);
        })
            .catch(() => setTypes([]));
        // Fetch available phases from backend
        fetch("/api/phases")
            .then((r) => (r.ok ? r.json() : []))
            .then((data) => setPhases(Array.isArray(data) ? data : []))
            .catch(() => setPhases([]));
    }, []);
    const addType = async () => {
        if (!newName.trim())
            return;
        const body = {
            name: newName.trim(),
            template: `<h1>${newName.trim()}</h1>`,
            workflow: []
        };
        try {
            const r = await fetch("/api/document-types", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (r.ok) {
                const created = await r.json();
                setTypes([...types, { id: created.name, name: created.name, phases: [] }]);
            }
            else {
                toast.error("Failed to add document type");
            }
        }
        catch {
            toast.error("Failed to add document type");
        }
        setNewName("");
    };
    const checkUsage = async (docTypeName) => {
        try {
            const response = await fetch(`/api/document-types/${encodeURIComponent(docTypeName)}/usage`);
            if (response.ok) {
                const usage = await response.json();
                setUsageInfo(usage);
                return usage;
            }
        }
        catch (error) {
            console.error("Error checking usage:", error);
        }
        return null;
    };
    const removeType = async (id) => {
        const usage = await checkUsage(id);
        if (usage && usage.in_use) {
            setShowDeleteDialog(id);
            return;
        }
        try {
            const res = await fetch(`/api/document-types/${encodeURIComponent(id)}`, { method: "DELETE" });
            if (res.ok) {
                setTypes(types.filter((t) => t.id !== id));
            }
            else {
                toast.error("Failed to delete document type");
            }
        }
        catch {
            toast.error("Failed to delete document type");
        }
    };
    const confirmDelete = async () => {
        if (!showDeleteDialog || !replacementDocType)
            return;
        try {
            const response = await fetch(`/api/document-types/${encodeURIComponent(showDeleteDialog)}?replacement=${encodeURIComponent(replacementDocType)}`, { method: "DELETE" });
            if (response.ok) {
                setTypes(types.filter((t) => t.id !== showDeleteDialog));
            }
            else {
                const error = await response.json();
                toast.error(`Error: ${error.detail}`);
            }
        }
        catch (error) {
            console.error("Error deleting document type:", error);
            toast.error("Error deleting document type");
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
    const startEdit = (t) => {
        setEditingId(t.id);
        setEditName(t.name);
    };
    const saveEdit = async (id) => {
        if (!editName.trim())
            return;
        const body = { name: editName.trim() };
        try {
            const res = await fetch(`/api/document-types/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                throw new Error("Failed to update document type");
            }
            setTypes(types.map((t) => (t.id === id ? { ...t, name: body.name } : t)));
            setEditingId(null);
            setEditName("");
            return;
        }
        catch {
            toast.error("Failed to update document type");
        }
    };
    const cancelEdit = () => {
        setEditingId(null);
        setEditName("");
    };
    const changePhase = async (docTypeId, phase) => {
        const docType = types.find((t) => t.id === docTypeId);
        if (!docType)
            return;
        const currentPhases = docType.phases || [];
        const updatedPhases = currentPhases.includes(phase)
            ? currentPhases.filter((p) => p !== phase)
            : [...currentPhases, phase];
        try {
            const res = await fetch(`/api/document-types/${encodeURIComponent(docTypeId)}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: docType.name,
                    template: docType.template || `<h1>${docType.name}</h1>`,
                    workflow: updatedPhases,
                }),
            });
            if (!res.ok) {
                throw new Error("Failed to update document type phases");
            }
            setTypes(types.map((t) => (t.id === docTypeId ? { ...t, phases: updatedPhases } : t)));
        }
        catch {
            toast.error("Failed to update document type phases");
        }
    };
    return (<div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Document Types</h1>
      <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); addType(); }}>
        <Input placeholder="New Document Type" value={newName} onChange={(e) => setNewName(e.target.value)} className="max-w-xs"/>
        <Button type="submit" size="sm">Add</Button>
      </form>
      <Table caption="Document types">
        <TableHeader>
          <TableRow>
            <TableHead>Document Type</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
            <TableHead>Attached Phase</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {types.map((t) => (<TableRow key={t.id}>
              <TableCell className="min-w-[150px]">
                {editingId === t.id ? (<Input value={editName} onChange={(e) => setEditName(e.target.value)} className="h-8"/>) : (t.name)}
              </TableCell>
              <TableCell className="w-28">
                {editingId === t.id ? (<div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(t.id)}>Save</Button>
                    <Button size="sm" variant="ghost" onClick={cancelEdit}>Cancel</Button>
                  </div>) : (<Button variant="ghost" size="icon" onClick={() => startEdit(t)} title="Edit" aria-label="Edit">
                    <Pencil className="w-4 h-4"/>
                  </Button>)}
              </TableCell>
              <TableCell className="w-20">
                <Button variant="ghost" size="icon" onClick={() => removeType(t.id)} title="Remove" aria-label="Remove">
                  <Trash className="w-4 h-4 text-red-600"/>
                </Button>
              </TableCell>
              <TableCell>
                <PhaseSelector docTypeId={t.id} phases={phases} selectedPhases={t.phases || []} changePhase={changePhase}/>
              </TableCell>
            </TableRow>))}
          {types.length === 0 && (<TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No document types defined.
              </TableCell>
            </TableRow>)}
        </TableBody>
      </Table>

      {showDeleteDialog && (<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Delete Document Type</h3>
            {usageInfo && (<div className="mb-4">
                <p className="text-red-600 mb-2">
                  This document type is currently in use by {usageInfo.usage_count} item(s):
                </p>
                {usageInfo.projects && usageInfo.projects.length > 0 && (<div className="mb-2">
                    <p className="font-medium">Projects:</p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {usageInfo.projects.map((project) => (<li key={project.id}>{project.name}</li>))}
                    </ul>
                  </div>)}
              </div>)}
            <p className="mb-4">
              Please select a replacement document type to assign to all affected projects:
            </p>
            <Select value={replacementDocType} onValueChange={setReplacementDocType}>
              <SelectTrigger>
                <SelectValue placeholder="Select replacement document type"/>
              </SelectTrigger>
              <SelectContent>
                {types
                .filter(t => t.id !== showDeleteDialog)
                .map((type) => (<SelectItem key={type.id} value={type.id}>
                      {type.name}
                    </SelectItem>))}
              </SelectContent>
            </Select>
            <div className="flex gap-2 mt-6">
              <Button onClick={confirmDelete} disabled={!replacementDocType} variant="danger">
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
