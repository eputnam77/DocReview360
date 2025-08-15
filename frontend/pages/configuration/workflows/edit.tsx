import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardHeader, CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { GripVertical, PlusCircle, Trash } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";

export default function EditWorkflowPage() {
  const router = useRouter();
  const { id } = router.query;
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<any[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [role, setRole] = useState("");
  const [user, setUser] = useState("");
  const [required, setRequired] = useState(true);

  useEffect(() => {
    fetch("/api/workflows/roles")
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          setRoles(data);
          setRole(data[0] ?? "");
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!router.isReady || !id) return;
    const wfId = Array.isArray(id) ? id[0] : id;
    fetch(`/api/workflows/${wfId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((wf) => {
        if (wf) {
          const wfName = wf.name ?? wf.project ?? wf.template ?? wf.id;
          setName(wfName);
          setDescription(wf.description ?? "");
          const loadedSteps = Array.isArray(wf.steps)
            ? wf.steps
            : Array.isArray(wf.approval_steps)
              ? wf.approval_steps.map((s: any, idx: number) => ({
                  id: s.id ?? idx,
                  role: s.role ?? s.name ?? "",
                  user: s.user ?? "",
                  required: typeof s.required === "boolean" ? s.required : true,
                }))
              : Array.isArray(wf.phases)
                ? wf.phases.map((p: any, idx: number) => ({
                    id: idx,
                    role: typeof p === "string" ? p : String(p),
                    user: "",
                    required: true,
                  }))
                : [];
          setSteps(loadedSteps);
        }
      })
      .catch(() => {});
  }, [id, router.isReady]);

  const addStep = () => {
    setSteps([
      ...steps,
      { id: "s" + (Math.random() * 10000).toFixed(0), role, user, required },
    ]);
    setRole(roles[0] ?? "");
    setUser("");
    setRequired(true);
  };
  const removeStep = (id: string) => setSteps(steps.filter(s => s.id !== id));
  const moveStep = (from: number, to: number) => {
    if (to < 0 || to >= steps.length) return;
    const arr = [...steps];
    const [moved] = arr.splice(from, 1);
    arr.splice(to, 0, moved);
    setSteps(arr);
  };
  const toggleRequired = (id: string) => {
    setSteps(steps.map(s =>
      s.id === id ? { ...s, required: !s.required } : s
    ));
  };
  const handleSave = () => {
    // Submit to API here
    alert("Workflow updated:\n" + JSON.stringify({ name, description, steps }, null, 2));
  };

  return (
    <div className="p-8 space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Edit Workflow</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid md:grid-cols-2 gap-4">
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Workflow Name"
              className="font-bold"
              required
            />
            <Input
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Description"
              required
            />
          </div>
          <form
            className="flex flex-wrap gap-2 items-end"
            onSubmit={e => { e.preventDefault(); addStep(); }}
          >
            <select
              value={role}
              onChange={e => setRole(e.target.value)}
              className="rounded border px-2 py-1"
            >
              {roles.map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            <Input
              placeholder="User or placeholder (optional)"
              value={user}
              onChange={e => setUser(e.target.value)}
              className="w-40"
            />
            <label className="inline-flex items-center gap-1 ml-2 text-xs">
              <input
                type="checkbox"
                checked={required}
                onChange={e => setRequired(e.target.checked)}
                className="mr-1"
              />
              Required
            </label>
            <Button type="submit" size="sm" className="ml-2" variant="outline">
              <PlusCircle className="w-4 h-4 mr-1" />
              Add Step
            </Button>
          </form>
          <Table caption="Workflow steps">
            <TableHeader>
              <TableRow>
                <TableHead>Order</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Required</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {steps.map((s, idx) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <div className="flex gap-1 items-center">
                      <button
                        onClick={() => moveStep(idx, idx - 1)}
                        disabled={idx === 0}
                        className="p-0 text-xs"
                        title="Move up"
                      >↑</button>
                      <button
                        onClick={() => moveStep(idx, idx + 1)}
                        disabled={idx === steps.length - 1}
                        className="p-0 text-xs"
                        title="Move down"
                      >↓</button>
                      <GripVertical className="w-3 h-3 text-gray-400 ml-2" />
                    </div>
                  </TableCell>
                  <TableCell>{s.role}</TableCell>
                  <TableCell>{s.user || <span className="text-gray-400">—</span>}</TableCell>
                  <TableCell>
                    <label className="inline-flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={s.required}
                        onChange={() => toggleRequired(s.id)}
                        className="mr-1"
                      />
                      <span className="text-xs">Required</span>
                    </label>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Remove step"
                      aria-label="Remove step"
                      onClick={() => removeStep(s.id)}
                    >
                      <Trash className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {steps.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                    No steps added yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          <div className="flex justify-end pt-4">
            <Button
              size="lg"
              onClick={handleSave}
              disabled={!name || !description || steps.length === 0}
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              Update Workflow
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
