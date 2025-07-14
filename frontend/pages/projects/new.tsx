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

const DOCUMENT_TYPES = [
  "Advisory Circular",
  "Policy Statement",
  "Release Notes",
];

const PHASES = ["Proposed", "Public Comment", "Final Issuance"];

const WORKFLOWS = [
  "Advisory Circular Standard Review",
  "Employee Onboarding",
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

  const manualWorkflow = useRef(false);

  useEffect(() => {
    manualWorkflow.current = false;
  }, [docType, phase]);

  useEffect(() => {
    if (!manualWorkflow.current && docType && phase) {
      const def = DEFAULT_WORKFLOW_MAP[phase]?.[docType];
      if (def) setWorkflow(def);
    }
  }, [docType, phase]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!docNumber.trim() || !title.trim() || !docType || !phase || !workflow) {
      setError("Please fill all required fields.");
      return;
    }
    if (files.length === 0) {
      setError("Please upload at least one file.");
      return;
    }

    setLoading(true);

    // Use FormData for file upload
    const formData = new FormData();
    formData.append("docNumber", docNumber);
    formData.append("title", title);
    formData.append("sme", sme);
    formData.append("docType", docType);
    if (phase) formData.append("phase", phase);
    if (workflow) formData.append("workflow", workflow);
    formData.append("description", description);
    files.forEach((f) => formData.append("files", f));

    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        body: formData,
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
            <Label htmlFor="docNumber">Document Number *</Label>
            <Input
              id="docNumber"
              value={docNumber}
              onChange={(e) => setDocNumber(e.target.value)}
              placeholder="E.g., AC 120-76E"
              required
            />
          </div>
          <div>
            <Label htmlFor="title">Document Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title of the document"
              required
            />
          </div>
          <div>
            <Label htmlFor="sme">Subject Matter Expert (SME)</Label>
            <Input
              id="sme"
              value={sme}
              onChange={(e) => setSme(e.target.value)}
              placeholder="Optional"
            />
          </div>
          <div>
            <Label htmlFor="docType">Document Type *</Label>
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger id="docType">
                <SelectValue placeholder="Select a document type" />
              </SelectTrigger>
              <SelectContent>
                {DOCUMENT_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="phase">Phase *</Label>
            <Select value={phase} onValueChange={setPhase}>
              <SelectTrigger id="phase">
                <SelectValue placeholder="Select a phase" />
              </SelectTrigger>
              <SelectContent>
                {PHASES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="workflow">Workflow *</Label>
            <Select
              value={workflow}
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
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Project description (optional)"
            />
          </div>
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
