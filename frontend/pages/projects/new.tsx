import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/router";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import UploadDropzone from "@/components/workflow/UploadDropzone";

function FieldGate({ when, children }: { when: boolean; children: React.ReactNode }) {
  return when ? <>{children}</> : null;
}


const WORKFLOWS = [
  "FAA Review",
  "Public Comment",
];

const DEFAULT_WORKFLOW_MAP: Record<string, Record<string, string>> = {
  Proposed: {
    "Advisory Circular": "Advisory Circular Standard Review",
    "Policy Statement": "Employee Onboarding",
    "Release Notes": "Employee Onboarding",
  },
  "Public Comment": {
    "Advisory Circular": "Advisory Circular Standard Review",
    "Policy Statement": "Employee Onboarding",
    "Release Notes": "Employee Onboarding",
  },
  "Final Issuance": {
    "Advisory Circular": "Advisory Circular Standard Review",
    "Policy Statement": "Employee Onboarding",
    "Release Notes": "Employee Onboarding",
  },
};

export default function NewProjectPage() {
  const router = useRouter();
  // Document Number is provided by the user. The immutable Document ID will be
  // generated server-side when the project is created.
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [phases, setPhases] = useState<string[]>([]);
  const [docNumber, setDocNumber] = useState("");
  const [title, setTitle] = useState("");
  const [sme, setSme] = useState("");
  const [docType, setDocType] = useState<string | undefined>(undefined);
  const [phase, setPhase] = useState<string | undefined>(undefined);
  const [workflow, setWorkflow] = useState<string | undefined>(undefined);
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const manualWorkflow = useRef(false);

  useEffect(() => {
    fetch("/api/document-types")
      .then((r) => r.json())
      .then((data) => setDocTypes(data.map((d: any) => d.name)))
      .catch(() => setDocTypes([]));
    fetch("/api/phases")
      .then((r) => r.json())
      .then(setPhases)
      .catch(() => setPhases([]));
  }, []);

  useEffect(() => {
    manualWorkflow.current = false;
  }, [docType, phase]);

  useEffect(() => {
    if (!manualWorkflow.current && docType && phase) {
      const def = DEFAULT_WORKFLOW_MAP[phase]?.[docType];
      if (def) setWorkflow(def);
    }
  }, [docType, phase]);

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!docType) errs.docType = "Required";
    if (!docNumber.trim()) errs.docNumber = "Required";
    if (!title.trim()) errs.title = "Required";
    if (!phase) errs.phase = "Required";
    if (!workflow) errs.workflow = "Required";
    if (files.length === 0) errs.files = "Upload at least one";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!validate()) {
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: docNumber,
          name: title,
          user: sme || undefined,
          doc_type: docType,
          phase,
          workflow,
          description,
        }),
      });
      if (!res.ok) throw new Error("Failed to create project");
      // Redirect to projects list or new project page
      router.push("/projects");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-xl mx-auto bg-white shadow-lg rounded-xl p-8">
        <h1 className="text-2xl font-bold mb-6">Create New Project</h1>
        <form
          className="space-y-5"
          onSubmit={handleSubmit}
          encType="multipart/form-data"
        >
          <div>
            <Label htmlFor="docType">Document Type *</Label>
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger id="docType">
                <SelectValue placeholder="Select a document type" />
              </SelectTrigger>
              <SelectContent>
                {docTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {fieldErrors.docType && (
              <p className="text-sm text-red-600">{fieldErrors.docType}</p>
            )}
          </div>
          <div>
            <Label htmlFor="docNumber">Document Number *</Label>
            <Input
              id="docNumber"
              value={docNumber}
              onChange={(e) => setDocNumber(e.target.value)}
              onBlur={validate}
              placeholder="E.g., AC 120-76E"
              aria-invalid={!!fieldErrors.docNumber}
            />
            {fieldErrors.docNumber && (
              <p className="text-sm text-red-600">{fieldErrors.docNumber}</p>
            )}
          </div>
          <div>
            <Label htmlFor="title">Document Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onBlur={validate}
              placeholder="Title of the document"
              aria-invalid={!!fieldErrors.title}
            />
            {fieldErrors.title && (
              <p className="text-sm text-red-600">{fieldErrors.title}</p>
            )}
          </div>
          <div>
            <Label htmlFor="phase">Phase *</Label>
            <Select value={phase} onValueChange={setPhase}>
              <SelectTrigger id="phase">
                <SelectValue placeholder="Select a phase" />
              </SelectTrigger>
              <SelectContent>
                {phases.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {fieldErrors.phase && (
              <p className="text-sm text-red-600">{fieldErrors.phase}</p>
            )}
          </div>
          <FieldGate when={!!docType && !!phase}>
            <div>
              <Label htmlFor="workflow">Workflow *</Label>
              <Select
                value={workflow}
                disabled={!docType || !phase}
                onValueChange={(v) => {
                  manualWorkflow.current = true;
                  setWorkflow(v);
                }}
              >
                <SelectTrigger id="workflow">
                  <SelectValue placeholder="Select a workflow" />
                </SelectTrigger>
                <SelectContent>
                  {WORKFLOWS.map((w) => (
                    <SelectItem key={w} value={w}>
                      {w}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500">
                Suggested based on '{docType}' in '{phase}' phase.
              </p>
              {fieldErrors.workflow && (
                <p className="text-sm text-red-600">{fieldErrors.workflow}</p>
              )}
            </div>
          </FieldGate>
          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-gray-600">
              Additional details (optional)
            </summary>
            <div className="pt-3 space-y-4">
              <div>
                <Label htmlFor="sme">Subject Matter Expert (SME) <span className="text-gray-500">(optional)</span></Label>
                <Input
                  id="sme"
                  value={sme}
                  onChange={(e) => setSme(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="description">Description <span className="text-gray-500">(optional)</span></Label>
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>
          </details>
          <div>
            <Label>Upload Reference Files (.docx, .pdf, .txt)</Label>
            <UploadDropzone
              value={files}
              onChange={(f) => setFiles(Array.isArray(f) ? f : f ? [f] : [])}
              accept=".docx,.pdf,.txt"
              maxSizeMB={20}
              multiple
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Creating..." : "Create Project"}
          </Button>
        </form>
      </div>
    </div>
  );
}
