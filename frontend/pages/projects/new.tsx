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
import { API, authenticatedFetch } from "@/lib/api";
import { useCreateProject } from "@/lib/useProjects";
import { useRouter } from "next/router";
import React, { useEffect, useState } from "react";

function FieldGate({ when, children }: { when: boolean; children: React.ReactNode }) {
  return when ? <>{children}</> : null;
}

export function mergeProjectPhases(
  configuredPhases: string[],
  docTypePhases: string[],
): string[] {
  const merged = [...configuredPhases, ...docTypePhases]
    .map((value) => (typeof value === "string" ? value.trim() : ""))
    .filter(Boolean);
  return Array.from(new Set(merged));
}

export function resolveDefaultWorkflow(
  docType: string | undefined,
  phase: string | undefined,
  docTypeDefaultTemplates: Record<string, string | undefined>,
  phaseWorkflowTemplates: Record<string, string | undefined>,
): string | undefined {
  if (docType && docTypeDefaultTemplates[docType]) {
    return docTypeDefaultTemplates[docType];
  }
  if (phase && phaseWorkflowTemplates[phase]) {
    return phaseWorkflowTemplates[phase];
  }
  return undefined;
}

export default function NewProjectPage() {
  const router = useRouter();
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [docTypeMap, setDocTypeMap] = useState<Record<string, string[]>>({});
  const [phases, setPhases] = useState<string[]>([]);
  const [configuredPhases, setConfiguredPhases] = useState<string[]>([]);
  const [docTypeDefaultTemplates, setDocTypeDefaultTemplates] = useState<
    Record<string, string | undefined>
  >({});
  const [phaseWorkflowTemplates, setPhaseWorkflowTemplates] = useState<
    Record<string, string | undefined>
  >({});
  const [docNumber, setDocNumber] = useState("");
  const [title, setTitle] = useState("");
  const [sme, setSme] = useState("");
  const [docType, setDocType] = useState<string | undefined>(undefined);
  const [phase, setPhase] = useState<string | undefined>(undefined);
  const [workflow, setWorkflow] = useState<string | undefined>(undefined);
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const createProject = useCreateProject();

  useEffect(() => {
    authenticatedFetch(`${API}/phases/config`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => {
        if (!Array.isArray(data)) {
          setConfiguredPhases([]);
          setPhaseWorkflowTemplates({});
          return;
        }

        const names: string[] = [];
        const phaseDefaults: Record<string, string | undefined> = {};

        data.forEach((item) => {
          if (!item || typeof item !== "object") return;
          const value = item as { name?: unknown; workflow_template_id?: unknown };
          const name = typeof value.name === "string" ? value.name.trim() : "";
          if (!name) return;
          names.push(name);
          if (
            typeof value.workflow_template_id === "string" &&
            value.workflow_template_id.trim()
          ) {
            phaseDefaults[name] = value.workflow_template_id.trim();
          }
        });

        setConfiguredPhases(names);
        setPhaseWorkflowTemplates(phaseDefaults);
      })
      .catch(() => {
        authenticatedFetch(`${API}/phases`)
          .then((r) => (r.ok ? r.json() : []))
          .then((data) => {
            const phaseNames = Array.isArray(data)
              ? data
                  .map((d: unknown) =>
                    typeof d === "string"
                      ? d
                      : typeof d === "object" && d !== null && "name" in d
                        ? String((d as { name?: unknown }).name ?? "")
                        : "",
                  )
                  .map((name) => name.trim())
                  .filter(Boolean)
              : [];
            setConfiguredPhases(phaseNames);
            setPhaseWorkflowTemplates({});
          })
          .catch(() => {
            setConfiguredPhases([]);
            setPhaseWorkflowTemplates({});
          });
      });
  }, []);

  useEffect(() => {
    authenticatedFetch(`${API}/document-types`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (!Array.isArray(data)) {
          setDocTypes([]);
          setDocTypeMap({});
          return;
        }
        const names: string[] = [];
        const map: Record<string, string[]> = {};
        const defaults: Record<string, string | undefined> = {};
        data.forEach((d: any) => {
          const name = typeof d === "string" ? d : d?.name;
          if (name) {
            names.push(name);
            const availablePhases = Array.isArray(d?.phases)
              ? (d.phases as string[])
              : Array.isArray(d?.workflow)
                ? (d.workflow as string[])
                : [];
            map[name] = availablePhases;
            const defaultTemplate =
              typeof d?.default_template_id === "string" && d.default_template_id.trim()
                ? d.default_template_id
                : undefined;
            defaults[name] = defaultTemplate;
          }
        });
        setDocTypes(names);
        setDocTypeMap(map);
        setDocTypeDefaultTemplates(defaults);
      })
      .catch(() => {
        setDocTypes([]);
        setDocTypeMap({});
        setDocTypeDefaultTemplates({});
      });
  }, []);

  useEffect(() => {
    const docTypePhases = docType ? docTypeMap[docType] || [] : [];
    setPhases(mergeProjectPhases(configuredPhases, docTypePhases));
    setPhase(undefined);
  }, [docType, docTypeMap, configuredPhases]);

  useEffect(() => {
    const resolved = resolveDefaultWorkflow(
      docType,
      phase,
      docTypeDefaultTemplates,
      phaseWorkflowTemplates,
    );
    setWorkflow(resolved);
  }, [docType, phase, docTypeDefaultTemplates, phaseWorkflowTemplates]);

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!docType) errs.docType = "Required";
    if (!docNumber.trim()) errs.docNumber = "Required";
    if (!title.trim()) errs.title = "Required";
    if (!phase) errs.phase = "Required";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!validate()) {
      return;
    }

    const projectData = {
      document_number: docNumber,
      name: title,
      user: sme || undefined,
      doc_type: docType,
      phase,
      description,
    };
    if (workflow) {
      projectData.workflow = workflow;
    }

    try {
      await createProject.mutateAsync(projectData);
      router.push("/projects");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-xl rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-6 text-2xl font-bold">Create New Project</h1>
        <form className="space-y-5" onSubmit={handleSubmit} encType="multipart/form-data">
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
            {fieldErrors.docType && <p className="text-sm text-red-600">{fieldErrors.docType}</p>}
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
            {fieldErrors.docNumber && <p className="text-sm text-red-600">{fieldErrors.docNumber}</p>}
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
            {fieldErrors.title && <p className="text-sm text-red-600">{fieldErrors.title}</p>}
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
            {fieldErrors.phase && <p className="text-sm text-red-600">{fieldErrors.phase}</p>}
          </div>
          <FieldGate when={!!docType && !!phase}>
            <div>
              <Label htmlFor="workflow">Workflow</Label>
              <Input id="workflow" value={workflow || ""} disabled={true} placeholder="Assigned by backend" />
              <p className="text-xs text-gray-500">
                Assigned from document type defaults, or from selected phase defaults.
              </p>
            </div>
          </FieldGate>
          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-gray-600">Additional details (optional)</summary>
            <div className="space-y-4 pt-3">
              <div>
                <Label htmlFor="sme">
                  Subject Matter Expert (SME) <span className="text-gray-500">(optional)</span>
                </Label>
                <Input id="sme" value={sme} onChange={(e) => setSme(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="description">
                  Description <span className="text-gray-500">(optional)</span>
                </Label>
                <Input id="description" value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
            </div>
          </details>
          <div>
            <Label>
              Upload Reference Files (.docx, .pdf, .txt) <span className="text-gray-500">(optional)</span>
            </Label>
            <UploadDropzone
              value={files}
              onChange={(f) => setFiles(Array.isArray(f) ? f : f ? [f] : [])}
              accept=".docx,.pdf,.txt"
              maxSizeMB={20}
              multiple
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={createProject.isPending} className="w-full">
            {createProject.isPending ? "Creating..." : "Create Project"}
          </Button>
        </form>
      </div>
    </div>
  );
}
