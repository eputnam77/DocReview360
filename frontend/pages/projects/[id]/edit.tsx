import { Badge } from "@/components/ui/badge";
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
import { API, authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";
import { useRouter } from "next/router";
import React, { useEffect, useRef, useState } from "react";

interface WorkflowTemplate {
  id: string;
  name?: string;
  description?: string;
}

type ProjectData = {
  id: string;
  number?: string;
  name?: string;
  user?: string;
  doc_type?: string;
  phase?: string;
  description?: string;
  workflow?: string;
};

export type EditProjectPayloadArgs = {
  docNumber: string;
  title: string;
  docType: string;
  phase: string;
  description: string;
  sme: string;
  selectedWorkflow: string;
  username: string;
  isAdmin: boolean;
};

export function buildEditProjectPayload(
  args: EditProjectPayloadArgs,
): { error?: string; payload?: Record<string, unknown> } {
  if (!String(args.docNumber).trim() || !args.title.trim() || !args.docType || !args.phase) {
    return { error: "Please fill all required fields." };
  }

  const trimmedSme = args.sme.trim();
  if (trimmedSme && !args.isAdmin && args.username && trimmedSme !== args.username) {
    return { error: "You do not have permission to assign this project to another user." };
  }

  const payload: Record<string, unknown> = {
    name: args.title,
    doc_type: args.docType,
    phase: args.phase,
    description: args.description,
  };

  if (trimmedSme) {
    payload.user = trimmedSme;
  }
  if (args.selectedWorkflow) {
    payload.workflow = args.selectedWorkflow;
  }

  return { payload };
}

export async function readProjectUpdateError(
  res: Pick<Response, "status" | "json" | "text">,
): Promise<string> {
  let detail = `Failed to update project (${res.status})`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string" && data.detail.trim()) {
      detail = data.detail;
    } else if (typeof data?.error === "string" && data.error.trim()) {
      detail = data.error;
    }
  } catch {
    const text = await res.text().catch(() => "");
    if (text.trim()) {
      detail = text;
    }
  }
  return detail;
}

export function resolveEditWorkflowSuggestion(
  docType: string,
  phase: string,
  docTypeDefaultTemplates: Record<string, string | undefined>,
  phaseWorkflowTemplates: Record<string, string | undefined>,
): string {
  if (docType && docTypeDefaultTemplates[docType]) {
    return docTypeDefaultTemplates[docType] || "";
  }
  if (phase && phaseWorkflowTemplates[phase]) {
    return phaseWorkflowTemplates[phase] || "";
  }
  return "";
}

function mergePhases(configuredPhases: string[], docTypePhases: string[]): string[] {
  const merged = [...configuredPhases, ...docTypePhases]
    .map((value) => value.trim())
    .filter(Boolean);
  return Array.from(new Set(merged));
}

export default function EditProjectPage() {
  const router = useRouter();
  const { id } = router.query;
  const username = useUserStore((s) => s.username);
  const isAdmin = useUserStore((s) => s.isAdmin);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [docId, setDocId] = useState("");
  const [docNumber, setDocNumber] = useState("");
  const [title, setTitle] = useState("");
  const [sme, setSme] = useState("");
  const [docType, setDocType] = useState<string>("");
  const [phase, setPhase] = useState<string>("");
  const [description, setDescription] = useState("");

  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("");
  const [phases, setPhases] = useState<string[]>([]);
  const [configuredPhases, setConfiguredPhases] = useState<string[]>([]);
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [docTypeMap, setDocTypeMap] = useState<Record<string, string[]>>({});
  const [docTypeDefaultTemplates, setDocTypeDefaultTemplates] = useState<
    Record<string, string | undefined>
  >({});
  const [phaseWorkflowTemplates, setPhaseWorkflowTemplates] = useState<
    Record<string, string | undefined>
  >({});

  const manualWorkflow = useRef(false);

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    authenticatedFetch(`${API}/projects/${id}`)
      .then((r) => {
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}`);
        }
        return r.json() as Promise<ProjectData>;
      })
      .then(async (proj) => {
        setDocId(proj.id || "");
        setDocNumber(String(proj.number || ""));
        setTitle(proj.name || "");
        setSme(proj.user || "");
        setDocType(proj.doc_type || "");
        setPhase(proj.phase || "");
        setDescription(proj.description || proj.name || "");

        if (proj.workflow) {
          const wfRes = await authenticatedFetch(`${API}/workflows/${proj.workflow}`);
          if (wfRes.ok) {
            const wf = await wfRes.json();
            setSelectedWorkflow(wf.template ?? wf.id ?? "");
            manualWorkflow.current = true;
          }
        }
      })
      .catch(() => {
        setError("Could not load project.");
      })
      .finally(() => {
        setLoading(false);
      });

    fetch("/api/workflow-templates")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => {
        if (!Array.isArray(data)) {
          setWorkflows([]);
          return;
        }
        const items: WorkflowTemplate[] = data
          .map((item) => {
            if (!item || typeof item !== "object") return null;
            const value = item as { id?: unknown; name?: unknown; description?: unknown };
            const templateId = typeof value.id === "string" ? value.id : "";
            if (!templateId) return null;
            return {
              id: templateId,
              name: typeof value.name === "string" ? value.name : templateId,
              description:
                typeof value.description === "string" ? value.description : undefined,
            };
          })
          .filter(Boolean) as WorkflowTemplate[];
        setWorkflows(items);
      })
      .catch(() => {
        setWorkflows([]);
      });

    fetch("/api/phases/config")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => {
        if (!Array.isArray(data)) {
          setConfiguredPhases([]);
          setPhaseWorkflowTemplates({});
          return;
        }

        const names: string[] = [];
        const defaults: Record<string, string | undefined> = {};
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
            defaults[name] = value.workflow_template_id.trim();
          }
        });
        setConfiguredPhases(names);
        setPhaseWorkflowTemplates(defaults);
      })
      .catch(() => {
        setConfiguredPhases([]);
        setPhaseWorkflowTemplates({});
      });

    fetch("/api/document-types")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => {
        if (!Array.isArray(data)) {
          setDocTypes([]);
          setDocTypeMap({});
          setDocTypeDefaultTemplates({});
          return;
        }
        const names: string[] = [];
        const phaseMap: Record<string, string[]> = {};
        const defaults: Record<string, string | undefined> = {};

        data.forEach((item) => {
          if (!item || typeof item !== "object") return;
          const value = item as {
            name?: unknown;
            phases?: unknown;
            workflow?: unknown;
            default_template_id?: unknown;
          };
          const name = typeof value.name === "string" ? value.name : "";
          if (!name) return;
          names.push(name);
          const dtPhases = Array.isArray(value.phases)
            ? value.phases.filter((phaseName): phaseName is string => typeof phaseName === "string")
            : Array.isArray(value.workflow)
              ? value.workflow.filter((phaseName): phaseName is string => typeof phaseName === "string")
              : [];
          phaseMap[name] = dtPhases;
          defaults[name] =
            typeof value.default_template_id === "string" && value.default_template_id.trim()
              ? value.default_template_id
              : undefined;
        });

        setDocTypes(names);
        setDocTypeMap(phaseMap);
        setDocTypeDefaultTemplates(defaults);
      })
      .catch(() => {
        setDocTypes([]);
        setDocTypeMap({});
        setDocTypeDefaultTemplates({});
      });
  }, [id]);

  useEffect(() => {
    const docTypePhases = docType ? docTypeMap[docType] || [] : [];
    setPhases(mergePhases(configuredPhases, docTypePhases));
  }, [docType, docTypeMap, configuredPhases]);

  useEffect(() => {
    if (manualWorkflow.current) return;
    const suggestion = resolveEditWorkflowSuggestion(
      docType,
      phase,
      docTypeDefaultTemplates,
      phaseWorkflowTemplates,
    );
    setSelectedWorkflow(suggestion);
  }, [docType, phase, docTypeDefaultTemplates, phaseWorkflowTemplates]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const outcome = buildEditProjectPayload({
      docNumber,
      title,
      docType,
      phase,
      description,
      sme,
      selectedWorkflow,
      username,
      isAdmin,
    });

    if (outcome.error) {
      setError(outcome.error);
      return;
    }

    setLoading(true);

    try {
      const res = await authenticatedFetch(`${API}/projects/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(outcome.payload ?? {}),
      });
      if (!res.ok) {
        throw new Error(await readProjectUpdateError(res));
      }
      router.push(`/projects/${id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !docId) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-xl rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-6 text-2xl font-bold">Edit Project</h1>
        <form className="space-y-5" onSubmit={handleSubmit} encType="multipart/form-data">
          <div>
            <Label htmlFor="docId">Document ID</Label>
            <Input
              id="docId"
              type="text"
              value={docId}
              readOnly
              disabled
              className="w-full cursor-not-allowed bg-gray-100"
            />
            <p className="mt-1 text-xs text-gray-500">Document ID cannot be changed</p>
          </div>

          <div>
            <Label htmlFor="docType">Document Type *</Label>
            <Select
              value={docType}
              onValueChange={(value) => {
                setDocType(value);
                manualWorkflow.current = false;
              }}
            >
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
          </div>

          <div>
            <Label htmlFor="docNumber">Document Number *</Label>
            <Input
              id="docNumber"
              value={docNumber}
              onChange={(e) => setDocNumber(e.target.value)}
              placeholder="E.g., AC 120-76E"
            />
          </div>

          <div>
            <Label htmlFor="title">Document Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title of the document"
            />
          </div>

          <div>
            <Label htmlFor="phase">Phase *</Label>
            <Select
              value={phase}
              onValueChange={(newPhase) => {
                setPhase(newPhase);
                manualWorkflow.current = false;
              }}
            >
              <SelectTrigger id="phase">
                <SelectValue placeholder="Select a phase" />
              </SelectTrigger>
              <SelectContent>
                {phases.map((phaseName) => (
                  <SelectItem key={phaseName} value={phaseName}>
                    {phaseName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {phase && (
            <div>
              <Label htmlFor="workflow">Workflow *</Label>
              <Select
                value={selectedWorkflow}
                onValueChange={(workflowId) => {
                  setSelectedWorkflow(workflowId);
                  manualWorkflow.current = true;
                }}
              >
                <SelectTrigger id="workflow">
                  <SelectValue placeholder="Select a workflow" />
                </SelectTrigger>
                <SelectContent>
                  {workflows.map((w) => (
                    <SelectItem key={w.id} value={w.id}>
                      {w.name || w.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!manualWorkflow.current && selectedWorkflow ? (
                <p className="mt-2 text-xs text-gray-500">
                  Auto-selected from document type and phase configuration.
                </p>
              ) : null}
            </div>
          )}

          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-gray-600">
              Additional details (optional)
            </summary>
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
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>
          </details>

          {selectedWorkflow && (
            <div className="rounded-lg bg-blue-50 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-blue-900">
                    {workflows.find((w) => w.id === selectedWorkflow)?.name || selectedWorkflow}
                  </h4>
                  <p className="text-sm text-blue-700">
                    {workflows.find((w) => w.id === selectedWorkflow)?.description || ""}
                  </p>
                </div>
                <Badge className="bg-blue-100 text-blue-800">Selected</Badge>
              </div>
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Saving..." : "Save Changes"}
          </Button>
        </form>
      </div>
    </div>
  );
}
