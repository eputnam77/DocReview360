import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import UploadDropzone from "@/components/workflow/UploadDropzone";
import { API } from "@/lib/api";
import { useRouter } from "next/router";
import React, { useEffect, useState } from "react";

function FieldGate({ when, children }: { when: boolean; children: React.ReactNode }) {
  return when ? <>{children}</> : null;
}



export default function NewProjectPage() {
  const router = useRouter();
  // Document Number is provided by the user. The immutable Document ID will be
  // generated server-side when the project is created.
  const DEMO_DOC_TYPES: string[] = [];
  const DEMO_PHASES: string[] = [];
  const [docTypes, setDocTypes] = useState<string[]>(DEMO_DOC_TYPES);
  const [phases, setPhases] = useState<string[]>(DEMO_PHASES);
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

  // Auto-set workflow based on selected phase
  useEffect(() => {
    if (phase) {
      setWorkflow(phase);
    }
  }, [phase]);

  useEffect(() => {
    console.log('Fetching document types from:', `${API}/document-types`);
    fetch(`${API}/document-types`)
      .then((r) => {
        console.log('Document types response status:', r.status);
        return r.ok ? r.json() : [];
      })
      .then((data) => {
        console.log('Document types API data:', data);
        const docTypeNames = data.length
          ? data.map((d: any) => (typeof d === "string" ? d : d.name))
          : DEMO_DOC_TYPES;
        console.log('Setting document types to:', docTypeNames);
        setDocTypes(docTypeNames);
      })
      .catch((error) => {
        console.error('Error fetching document types:', error);
        setDocTypes(DEMO_DOC_TYPES);
      });
    fetch(`${API}/phases`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        console.log('Phases API data:', data);
        const phaseNames = data.length
          ? data.map((d: any) => (typeof d === "string" ? d : d.name))
          : DEMO_PHASES;
        console.log('Setting phases to:', phaseNames);
        setPhases(phaseNames);
      })
      .catch((error) => {
        console.error('Error fetching phases:', error);
        setPhases(DEMO_PHASES);
      });
  }, []);

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!docType) errs.docType = "Required";
    if (!docNumber.trim()) errs.docNumber = "Required";
    if (!title.trim()) errs.title = "Required";
    if (!phase) errs.phase = "Required";
    if (!workflow) errs.workflow = "Required";
    // Remove file upload requirement - make it optional
    // if (files.length === 0) errs.files = "Upload at least one";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!validate()) {
      console.log('Validation failed:', fieldErrors);
      return;
    }

    setLoading(true);

    const projectData = {
      // Don't send id - let backend auto-generate it
      document_number: docNumber, // User-provided document number
      name: title,
      user: sme || undefined,
      doc_type: docType,
      phase,
      workflow,
      description,
    };

    console.log('Creating project with data:', projectData);

    try {
      const res = await fetch(`${API}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectData),
      });

      console.log('Response status:', res.status);

      if (!res.ok) {
        const errorText = await res.text();
        console.error('Error response:', errorText);
        throw new Error(`Failed to create project: ${res.status} ${errorText}`);
      }

      const result = await res.json();
      console.log('Project created successfully:', result);

      // Redirect to projects list or new project page
      router.push("/projects");
    } catch (err) {
      console.error('Error creating project:', err);
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
              <Input
                id="workflow"
                value={workflow || ""}
                disabled={true}
                placeholder="Auto-selected based on phase"
              />
              <p className="text-xs text-gray-500">Automatically set based on selected phase.</p>
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
            <Label>Upload Reference Files (.docx, .pdf, .txt) <span className="text-gray-500">(optional)</span></Label>
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
