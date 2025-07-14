import React, { useState, useEffect } from "react";
import {
  Card, CardHeader, CardTitle, CardContent,
} from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { PlusCircle, Trash, GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";


export default function NewWorkflowPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<any[]>([]);
  const [role, setRole] = useState("");
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [docType, setDocType] = useState<string | undefined>(undefined);
  const [user, setUser] = useState("");
  const [required, setRequired] = useState(true);

  useEffect(() => {
    fetch("/api/document-types")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => setDocTypes(data.map((d) => d.name)))
      .catch(() => setDocTypes([]));
  }, []);

  const addStep = () => {
    if (!role.trim()) return;
    setSteps([
      ...steps,
      { id: "s" + (Math.random() * 10000).toFixed(0), role, user, required },
    ]);
    setRole("");
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

  const handleSave = async () => {
    const payload = { name, description, steps };
    // naive demo submission
    await fetch("/api/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {});

    if (docType) {
      try {
        const res = await fetch(`/api/document-types/${docType}`);
        if (res.ok) {
          const doc = await res.json();
          const workflow = Array.isArray(doc.workflow) ? doc.workflow : [];
          if (!workflow.includes(name)) workflow.push(name);
          await fetch(`/api/document-types/${docType}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...doc, workflow }),
          });
        }
      } catch {
        // ignore errors in demo
      }
    }

    alert(
      "Workflow saved:\n" +
        JSON.stringify({ name, description, steps, docType }, null, 2)
    );
  };

  return (
    <div className="p-8 space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Create New Workflow</CardTitle>
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
          <div className="grid md:grid-cols-2 gap-4">
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger>
                <SelectValue placeholder="Attach Document Type (optional)" />
              </SelectTrigger>
              <SelectContent>
                {docTypes.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Add Step Form */}
          <form
            className="flex flex-wrap gap-2 items-end"
            onSubmit={e => { e.preventDefault(); addStep(); }}
          >
            <Input
              value={role}
              onChange={e => setRole(e.target.value)}
              placeholder="User role"
              className="w-48"
            />
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
          {/* Steps Table */}
          <Table>
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
                    <span className={cn(
                      "px-2 py-1 rounded text-xs font-medium",
                      s.required ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-500"
                    )}>{s.required ? "Yes" : "No"}</span>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Remove step"
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
              Save Workflow
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
