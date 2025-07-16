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

          {/* On-screen instructions */}
          <div className="mb-4 p-4 rounded-lg bg-blue-50 border border-blue-200 text-blue-900 text-sm">
            <ol className="list-decimal pl-5 space-y-1">
              <li>Enter a workflow name and description.</li>
              <li>Select a document type to attach (optional).</li>
              <li>
                Add one or more workflow steps below. Each step defines a user role, an optional user, and whether the step is required.
              </li>
              <li>Arrange steps in the order they should occur. When finished, click "Save Workflow".</li>
            </ol>
          </div>

          {/* Workflow name & description */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block mb-1 font-medium" htmlFor="workflow-name">
                Workflow Name <span className="text-red-500">*</span>
              </label>
              <Input
                id="workflow-name"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g., Policy Approval"
                className="font-bold"
                required
                aria-required="true"
              />
              <div className="text-xs text-gray-500 mt-1">Give your workflow a clear, descriptive name.</div>
            </div>
            <div>
              <label className="block mb-1 font-medium" htmlFor="workflow-desc">
                Description <span className="text-red-500">*</span>
              </label>
              <Input
                id="workflow-desc"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Short summary of this workflow"
                required
                aria-required="false"
              />
              <div className="text-xs text-gray-500 mt-1">Describe what this workflow does.</div>
            </div>
          </div>

          {/* Attach Document Type */}
          <div className="mt-4 md:w-1/2">
            <label className="block mb-1 font-medium" htmlFor="attach-doc-type">
              Attach Document Type (optional)
            </label>
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger id="attach-doc-type">
                <SelectValue placeholder="Choose a document type" />
              </SelectTrigger>
              <SelectContent>
                {docTypes.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="text-xs text-gray-500 mt-1">
              Link this workflow to a document type, if applicable.
            </div>
          </div>

          {/* Add Step Form */}
          <div className="mt-8">
            <div className="font-semibold mb-2">Add Workflow Step</div>
            <form
              className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end"
              onSubmit={e => { e.preventDefault(); addStep(); }}
              aria-label="Add workflow step"
            >
              <div>
                <label htmlFor="role" className="block mb-1 text-sm font-medium">
                  User Role <span className="text-red-500">*</span>
                </label>
                <Input
                  id="role"
                  value={role}
                  onChange={e => setRole(e.target.value)}
                  placeholder="e.g., Manager"
                  className="w-full"
                  required
                />
                <div className="text-xs text-gray-500 mt-1">Role assigned for this step (e.g., Manager, Reviewer).</div>
              </div>
              <div>
                <label htmlFor="user" className="block mb-1 text-sm font-medium">
                  User <span className="text-gray-400">(optional)</span>
                </label>
                <Input
                  id="user"
                  placeholder="Assign user or leave blank"
                  value={user}
                  onChange={e => setUser(e.target.value)}
                  className="w-full"
                />
                <div className="text-xs text-gray-500 mt-1">Assign a specific user, or leave blank for any user in this role.</div>
              </div>
              <div>
                <label htmlFor="required" className="block mb-1 text-sm font-medium">
                  Required?
                </label>
                <label className="inline-flex items-center gap-1">
                  <input
                    id="required"
                    type="checkbox"
                    checked={required}
                    onChange={e => setRequired(e.target.checked)}
                    className="mr-1"
                  />
                  <span className="text-sm">This step is required</span>
                </label>
                <div className="text-xs text-gray-500 mt-1">Uncheck if this step is optional in the workflow.</div>
              </div>
              <div className="flex items-end">
                <Button type="submit" size="sm" className="w-full" variant="outline">
                  <PlusCircle className="w-4 h-4 mr-1" />
                  Add Step
                </Button>
              </div>
            </form>
          </div>

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
