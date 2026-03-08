import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Pencil, Plus, Trash } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "react-hot-toast";
import { API, authenticatedFetch } from "@/lib/api";

interface DocType {
  id: string;
  name: string;
  phases?: string[];
  template?: string;
  default_template_id?: string;
}

interface TemplateOption {
  id: string;
  name: string;
}

const GOVERNMENT_FIRST_STARTER_SET = [
  { id: "advisory_circular", label: "Advisory Circular", category: "government", is_active: true },
  { id: "order_directive", label: "Order / Directive", category: "government", is_active: true },
  { id: "policy", label: "Policy", category: "government", is_active: true },
  { id: "guidance", label: "Guidance", category: "government", is_active: true },
  { id: "memorandum", label: "Memorandum", category: "government", is_active: true },
  { id: "sop", label: "SOP", category: "government", is_active: true },
  { id: "desk_guide", label: "Desk Guide", category: "government", is_active: true },
  { id: "manual_handbook", label: "Manual / Handbook", category: "government", is_active: true },
  { id: "report", label: "Report", category: "government", is_active: true },
  { id: "audit_report", label: "Audit Report", category: "government", is_active: true },
  { id: "after_action_report", label: "After-Action Report", category: "government", is_active: true },
  { id: "briefing_slide_deck", label: "Briefing / Slide Deck", category: "government", is_active: true },
  { id: "meeting_minutes", label: "Meeting Minutes", category: "government", is_active: true },
  { id: "federal_register_notice", label: "Federal Register Notice", category: "rulemaking", is_active: true },
  { id: "proposed_rule_nprm", label: "Proposed Rule / NPRM", category: "rulemaking", is_active: true },
  { id: "final_rule", label: "Final Rule", category: "rulemaking", is_active: true },
  { id: "supporting_statement_pra", label: "Supporting Statement (PRA)", category: "rulemaking", is_active: true },
  { id: "icr", label: "ICR", category: "rulemaking", is_active: true },
  { id: "exemption_waiver", label: "Exemption / Waiver", category: "rulemaking", is_active: true },
  { id: "special_conditions", label: "Special Conditions", category: "rulemaking", is_active: true },
  { id: "faq", label: "FAQ", category: "comms", is_active: true },
  { id: "letter_correspondence", label: "Letter / Correspondence", category: "comms", is_active: true },
  { id: "web_content", label: "Web Content", category: "comms", is_active: true },
  { id: "release_notes", label: "Release Notes", category: "technical", is_active: true },
  { id: "user_guide", label: "User Guide", category: "technical", is_active: true },
  { id: "api_manual_api_reference", label: "API Manual / API Reference", category: "technical", is_active: true },
  { id: "readme", label: "README", category: "technical", is_active: true },
] as const;
const normalizeDocTypes = (items: unknown): DocType[] => {
  if (!Array.isArray(items)) return [];
  const normalized: DocType[] = [];

  for (const item of items) {
    if (!item || typeof item !== "object") continue;

    const anyItem = item as {
      id?: unknown;
      name?: unknown;
      phases?: unknown;
      workflow?: unknown;
      template?: unknown;
    };
    const name =
      typeof anyItem.name === "string" && anyItem.name.trim()
        ? anyItem.name.trim()
        : "";
    if (!name) continue;

    const id =
      typeof anyItem.id === "string" && anyItem.id.trim()
        ? anyItem.id.trim()
        : name;

    let phases: string[] = [];
    if (Array.isArray(anyItem.phases)) {
      phases = (anyItem.phases as string[]).filter((p) => typeof p === "string" && p.trim());
    } else if (Array.isArray(anyItem.workflow)) {
      phases = (anyItem.workflow as string[]).filter((p) => typeof p === "string" && p.trim());
    }

    const template =
      typeof anyItem.template === "string" && anyItem.template.trim()
        ? anyItem.template
        : "";

    const default_template_id =
      typeof (anyItem as any).default_template_id === "string" && (anyItem as any).default_template_id.trim()
        ? (anyItem as any).default_template_id
        : undefined;

    normalized.push({
      id,
      name,
      ...(phases.length > 0 ? { phases } : {}),
      ...(template ? { template } : {}),
      ...(default_template_id ? { default_template_id } : {}),
    });
  }

  return normalized.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
};

function PhaseSelector({
  docTypeId,
  phases,
  selectedPhases,
  changePhase,
}: {
  docTypeId: string;
  phases: string[];
  selectedPhases: string[];
  changePhase: (docTypeId: string, phase: string) => void | Promise<void>;
}) {
  const [search, setSearch] = useState("");
  const filtered = phases.filter((p) =>
    p.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="flex flex-wrap items-center gap-1">
      {selectedPhases.length > 0 ? (
        selectedPhases.map((p) => (
          <Badge key={p} variant="outline" className="whitespace-nowrap">
            {p}
          </Badge>
        ))
      ) : (
        <span className="text-gray-400 text-xs italic">No phases</span>
      )}
      <Popover>
        <PopoverTrigger as={Fragment}>
          <Button size="sm" variant="outline" className="h-6 px-2 text-xs gap-1">
            <Plus className="w-3 h-3" />
            {selectedPhases.length ? "Edit" : "Add"}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-2">
          <Input
            placeholder="Search phases..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-2 h-8 text-xs"
          />
          <ScrollArea className="max-h-48">
            <div className="space-y-1">
              {filtered.map((p) => {
                const isSelected = selectedPhases.includes(p);
                return (
                  <label
                    key={p}
                    className="flex items-center space-x-2 cursor-pointer px-1 py-1 rounded hover:bg-gray-50"
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => changePhase(docTypeId, p)}
                      className="h-3 w-3"
                    />
                    <span className="text-sm">{p}</span>
                  </label>
                );
              })}
            </div>
          </ScrollArea>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export default function DocumentTypesPage() {
  const [types, setTypes] = useState<DocType[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [phases, setPhases] = useState<string[]>([]);
  const [templates, setTemplates] = useState<TemplateOption[]>([]);
  const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null);
  const [replacementDocType, setReplacementDocType] = useState<string>("");
  const [usageInfo, setUsageInfo] = useState<any>(null);
  const [seedingStarterSet, setSeedingStarterSet] = useState(false);

  useEffect(() => {
    // Fetch document types from backend
    authenticatedFetch(`${API}/document-types`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => {
        const list = normalizeDocTypes(data);
        setTypes(list);
      })
      .catch(() => setTypes([]));

    // Fetch available phases from backend
    authenticatedFetch(`${API}/phases`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: string[]) => setPhases(Array.isArray(data) ? data : []))
      .catch(() => setPhases([]));

    // Fetch available templates for default template selector
    authenticatedFetch(`${API}/templates`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => {
        if (Array.isArray(data)) {
          setTemplates(data.map((t) => ({ id: t.id || t.name, name: t.name || t.id })));
        }
      })
      .catch(() => setTemplates([]));
  }, []);

  const addType = async () => {
    if (!newName.trim()) return;
    const body = {
      name: newName.trim(),
      template: `<h1>${newName.trim()}</h1>`,
      workflow: []
    };
    try {
      const r = await authenticatedFetch(`${API}/document-types`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        const created = await r.json();
        setTypes(normalizeDocTypes([...types, { id: created.name, name: created.name, phases: [] }]));
      } else {
        toast.error("Failed to add document type");
      }
    } catch {
      toast.error("Failed to add document type");
    }
    setNewName("");
  };

  const addGovernmentStarterSet = async () => {
    if (seedingStarterSet) {
      return;
    }

    setSeedingStarterSet(true);
    try {
      const existing = new Set(types.map((t) => t.name.trim().toLowerCase()));
      const toCreate = GOVERNMENT_FIRST_STARTER_SET.filter(
        (item) => !existing.has(item.label.trim().toLowerCase()),
      );

      if (toCreate.length === 0) {
        toast("Government-first starter set is already present.");
        return;
      }

      let createdCount = 0;
      for (const item of toCreate) {
        const res = await authenticatedFetch(`${API}/document-types`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: item.id,
            name: item.label,
            label: item.label,
            category: item.category,
            is_active: item.is_active,
            template: `<h1>${item.label}</h1>`,
            workflow: [],
          }),
        });

        if (res.ok) {
          createdCount += 1;
        } else {
          const message = await res.text().catch(() => "");
          console.error(`Failed to create document type '${item.label}': ${message}`);
        }
      }

      const refreshed = await authenticatedFetch(`${API}/document-types`)
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => []);
      setTypes(normalizeDocTypes(refreshed));

      if (createdCount > 0) {
        toast.success(`Added ${createdCount} government-first document types.`);
      } else {
        toast.error("No document types were added.");
      }
    } finally {
      setSeedingStarterSet(false);
    }
  };
  const checkUsage = async (docTypeName: string) => {
    try {
      const response = await authenticatedFetch(
        `${API}/document-types/${encodeURIComponent(docTypeName)}/usage`,
      );
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
    const usage = await checkUsage(id);
    if (usage && usage.in_use) {
      setShowDeleteDialog(id);
      return;
    }
    try {
      const res = await authenticatedFetch(`${API}/document-types/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (res.ok) {
        setTypes(types.filter((t) => t.id !== id));
      } else {
        toast.error("Failed to delete document type");
      }
    } catch {
      toast.error("Failed to delete document type");
    }
  };

  const confirmDelete = async () => {
    if (!showDeleteDialog || !replacementDocType) return;
    try {
      const response = await authenticatedFetch(
        `${API}/document-types/${encodeURIComponent(showDeleteDialog)}?replacement=${encodeURIComponent(replacementDocType)}`,
        { method: "DELETE" }
      );
      if (response.ok) {
        setTypes(types.filter((t) => t.id !== showDeleteDialog));
      } else {
        const error = await response.json();
        toast.error(`Error: ${error.detail}`);
      }
    } catch (error) {
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

  const startEdit = (t: DocType) => {
    setEditingId(t.id);
    setEditName(t.name);
  };

  const saveEdit = async (id: string) => {
    if (!editName.trim()) return;
    const body = { name: editName.trim() };
    try {
      const res = await authenticatedFetch(`${API}/document-types/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error("Failed to update document type");
      }
      setTypes(normalizeDocTypes(types.map((t) => (t.id === id ? { ...t, name: body.name } : t))));
      setEditingId(null);
      setEditName("");
      return;
    } catch {
      toast.error("Failed to update document type");
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
  };

  const changeDefaultTemplate = async (docTypeId: string, templateId: string) => {
    const docType = types.find((t) => t.id === docTypeId);
    if (!docType) return;
    try {
      const res = await authenticatedFetch(`${API}/document-types/${encodeURIComponent(docTypeId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: docType.name,
          template: docType.template || `<h1>${docType.name}</h1>`,
          workflow: docType.phases || [],
          default_template_id: templateId || null,
        }),
      });
      if (!res.ok) throw new Error("Failed to update default template");
      setTypes(
        types.map((t) =>
          t.id === docTypeId ? { ...t, default_template_id: templateId || undefined } : t,
        ),
      );
    } catch {
      toast.error("Failed to update default template");
    }
  };

  const changePhase = async (docTypeId: string, phase: string) => {
    const docType = types.find((t) => t.id === docTypeId);
    if (!docType) return;
    const currentPhases = docType.phases || [];
    const updatedPhases = currentPhases.includes(phase)
      ? currentPhases.filter((p) => p !== phase)
      : [...currentPhases, phase];
    try {
      const res = await authenticatedFetch(`${API}/document-types/${encodeURIComponent(docTypeId)}`, {
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
      setTypes(
        types.map((t) => (t.id === docTypeId ? { ...t, phases: updatedPhases } : t)),
      );
    } catch {
      toast.error("Failed to update document type phases");
    }
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Document Types</h1>
      <p className="text-sm text-muted-foreground">Document types are optimized for federal and state document review, with support for common technical documentation.</p>
      <div className="flex flex-wrap items-end gap-2">
        <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); addType(); }}>
          <Input
            placeholder="New Document Type"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="max-w-xs"
          />
          <Button type="submit" size="sm">Add</Button>
        </form>
        <Button type="button" size="sm" variant="outline" onClick={addGovernmentStarterSet} disabled={seedingStarterSet}>
          {seedingStarterSet ? "Adding starter set..." : "Add Government Starter Set"}
        </Button>
      </div>
      <Table caption="Document types">
        <TableHeader>
          <TableRow>
            <TableHead>Document Type</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
            <TableHead>Attached Phase</TableHead>
            <TableHead>Default Template</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {types.map((t) => (
            <TableRow key={t.id}>
              <TableCell className="min-w-[150px]">
                {editingId === t.id ? (
                  <Input value={editName} onChange={(e) => setEditName(e.target.value)} className="h-8" />
                ) : (
                  t.name
                )}
              </TableCell>
              <TableCell className="w-28">
                {editingId === t.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(t.id)}>Save</Button>
                    <Button size="sm" variant="ghost" onClick={cancelEdit}>Cancel</Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => startEdit(t)}
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
                  onClick={() => removeType(t.id)}
                  title="Remove"
                  aria-label="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
              <TableCell>
                <PhaseSelector
                  docTypeId={t.id}
                  phases={phases}
                  selectedPhases={t.phases || []}
                  changePhase={changePhase}
                />
              </TableCell>
              <TableCell className="min-w-[180px]">
                <Select
                  value={t.default_template_id || ""}
                  onValueChange={(val) => changeDefaultTemplate(t.id, val)}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
                    {templates.map((tpl) => (
                      <SelectItem key={tpl.id} value={tpl.id}>
                        {tpl.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableCell>
            </TableRow>
          ))}
          {types.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No document types defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

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
              <Button onClick={confirmDelete} disabled={!replacementDocType} variant="danger">
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

