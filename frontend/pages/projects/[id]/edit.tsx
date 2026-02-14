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
import { CheckCircle, Clock, Users, Workflow, XCircle } from "lucide-react";
import { useRouter } from "next/router";
import React, { useEffect, useRef, useState } from "react";

interface WorkflowTemplate {
  id: string;
  name: string;
  project?: string;
  description?: string;
  steps?: Array<{
    role: string;
    user?: string;
    required?: boolean;
  }>;
  usage?: number;
  updated?: string;
}

interface Approval {
  id: string;
  reviewer: string;
  state: "pending" | "approved" | "rejected";
  due_at?: string;
  signed_at?: string;
  phaseId?: string;
  required?: boolean;
}

export default function EditProjectPage() {
  const router = useRouter();
  const { id } = router.query;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [docId, setDocId] = useState(""); // Document ID - read-only
  const [docNumber, setDocNumber] = useState(""); // Document Number - editable
  const [title, setTitle] = useState("");
  const [sme, setSme] = useState("");
  const [docType, setDocType] = useState<string>("");
  const [phase, setPhase] = useState<string>("");
  const [description, setDescription] = useState("");

  // Workflow and approval fields
  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("");
  const [currentApprovals, setCurrentApprovals] = useState<Approval[]>([]);
  const [showWorkflowSelector, setShowWorkflowSelector] = useState(false);
  const [phases, setPhases] = useState<string[]>([]);
  const [docTypes, setDocTypes] = useState<string[]>([]);

  const manualWorkflow = useRef(false);

  // Reset manual workflow flag when phase changes
  useEffect(() => {
    manualWorkflow.current = false;
  }, [docType, phase]);

  // Fetch project details and available workflows on mount
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    console.log('Edit page: Fetching project data from:', `${API}/projects/${id}`);

    // Fetch project data
    authenticatedFetch(`${API}/projects/${id}`)
      .then((r) => {
        console.log('Edit page: Response status:', r.status);
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}`);
        }
        return r.json();
      })
      .then(async (proj) => {
        console.log('Edit page: Received project data:', proj);
        // Map backend ProjectModel fields to frontend form fields
        setDocId(proj.id || ""); // Document ID - immutable
        setDocNumber(String(proj.number || "")); // Document Number - editable, ensure it's a string
        setTitle(proj.name || "");
        setSme(proj.user || "");
        setDocType(proj.doc_type || "");
        setPhase(proj.phase || "");
        setDescription(proj.description || proj.name || "");

        // Fetch workflow data if project has a workflow
        if (proj.workflow) {
          try {
            const wfRes = await authenticatedFetch(`${API}/workflows/${proj.workflow}`);
            if (wfRes.ok) {
              const workflow = await wfRes.json();
              setSelectedWorkflow(workflow.template ?? workflow.id);
            }
          } catch (error) {
            console.error('Failed to fetch workflow:', error);
          }

          // Fetch approvals for the workflow
          try {
            const apRes = await authenticatedFetch(`${API}/approvals?workflow=${proj.workflow}`);
            if (apRes.ok) {
              const approvals = await apRes.json();
              const mapped = approvals.map((a: any) => ({
                ...a,
                phaseId: a.phase_id,
                required: a.required,
              }));
              setCurrentApprovals(mapped);
            }
          } catch (error) {
            console.error('Failed to fetch approvals:', error);
          }
        } else {
          // If no workflow is associated, try to find workflow by project ID
          try {
            const wfRes = await authenticatedFetch(`${API}/workflows?project=${id}`);
            if (wfRes.ok) {
              const workflows = await wfRes.json();
              if (workflows.length > 0) {
                const projectWorkflow = workflows[0];
                setSelectedWorkflow(projectWorkflow.template ?? projectWorkflow.id);

                // Fetch approvals for this workflow
                const apRes = await authenticatedFetch(`${API}/approvals?workflow=${projectWorkflow.id}`);
                if (apRes.ok) {
                  const approvals = await apRes.json();
                  const mapped = approvals.map((a: any) => ({
                    ...a,
                    phaseId: a.phase_id,
                    required: a.required,
                  }));
                  setCurrentApprovals(mapped);
                }
              }
            }
          } catch (error) {
            console.error('Failed to fetch project workflow:', error);
          }
        }
        setLoading(false);
      })
      .catch((error) => {
        console.error('Edit page: API call failed:', error);
        setError('Could not load project.');
        setLoading(false);
      });

    // Fetch available workflow templates.
    fetch("/api/workflow-templates")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => {
        const list = Array.isArray(data) ? data : [];
        setWorkflows(list);
      })
      .catch(() => {
        setWorkflows([]);
      });

    // Fetch available phases
    fetch("/api/phases")
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        const phaseNames = Array.isArray(data)
          ? data.map((d: any) => (typeof d === "string" ? d : d.name))
          : [];
        setPhases(phaseNames);
      })
      .catch(() => {
        setPhases([]);
      });

    // Fetch available document types
    fetch("/api/document-types")
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        const docTypeNames = Array.isArray(data)
          ? data.map((d: any) => (typeof d === "string" ? d : d.name))
          : [];
        setDocTypes(docTypeNames);
      })
      .catch(() => {
        setDocTypes([]);
      });
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!String(docNumber).trim() || !title.trim() || !docType || !phase) {
      setError("Please fill all required fields.");
      return;
    }
    setLoading(true);

    try {
      const payload: Record<string, unknown> = {
        name: title,
        user: sme,
        doc_type: docType,
        phase,
        description,
      };
      if (selectedWorkflow) {
        payload.workflow = selectedWorkflow;
      }
      const res = await authenticatedFetch(`${API}/projects/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to update project");
      router.push(`/projects/${id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const getApprovalStatusIcon = (state: string) => {
    switch (state) {
      case "approved":
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case "rejected":
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-600" />;
    }
  };

  const getApprovalStatusBadge = (state: string) => {
    switch (state) {
      case "approved":
        return <Badge className="bg-green-100 text-green-800">Approved</Badge>;
      case "rejected":
        return <Badge className="bg-red-100 text-red-800">Rejected</Badge>;
      default:
        return <Badge className="bg-yellow-100 text-yellow-800">Pending</Badge>;
    }
  };

  const handlePhaseChange = (newPhase: string) => {
    setPhase(newPhase);
    manualWorkflow.current = false; // Reset manual flag when phase changes
  };

  const handleWorkflowChange = (workflowId: string) => {
    setSelectedWorkflow(workflowId);
    manualWorkflow.current = true; // Mark as manually selected
    setShowWorkflowSelector(false);
  };

  if (loading && !docId) return <div className="p-8">Loading…</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-xl mx-auto bg-white shadow-lg rounded-xl p-8">
        <h1 className="text-2xl font-bold mb-6">Edit Project</h1>
        <form
          className="space-y-5"
          onSubmit={handleSubmit}
          encType="multipart/form-data"
        >
          {/* Document ID - Read Only */}
          <div>
            <Label htmlFor="docId">Document ID</Label>
            <Input
              id="docId"
              type="text"
              value={docId}
              readOnly
              disabled
              className="w-full bg-gray-100 cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 mt-1">Document ID cannot be changed</p>
          </div>

          {/* Document Type */}
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
          </div>

          {/* Document Number - Editable */}
          <div>
            <Label htmlFor="docNumber">Document Number *</Label>
            <Input
              id="docNumber"
              value={docNumber}
              onChange={(e) => setDocNumber(e.target.value)}
              placeholder="E.g., AC 120-76E"
            />
          </div>

          {/* Document Title */}
          <div>
            <Label htmlFor="title">Document Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title of the document"
            />
          </div>

          {/* Phase */}
          <div>
            <Label htmlFor="phase">Phase *</Label>
            <Select value={phase} onValueChange={handlePhaseChange}>
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
          </div>

          {/* Workflow - Auto-suggested based on phase */}
          {phase && (
            <div>
              <Label htmlFor="workflow">Workflow *</Label>
              <Select
                value={selectedWorkflow}
                onValueChange={handleWorkflowChange}
              >
                <SelectTrigger id="workflow">
                  <SelectValue placeholder="Select a workflow" />
                </SelectTrigger>
                <SelectContent>
                  {workflows.map((w) => {
                    const wfName = w.name ?? w.project ?? w.id;
                    return (
                      <SelectItem key={w.id} value={w.id}>
                        <div className="flex items-center justify-between w-full">
                          <span>{wfName}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Additional Details */}
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

          {/* Current Workflow Status */}
          {selectedWorkflow && (
            <div className="border-t pt-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Workflow className="w-5 h-5" />
                  Current Workflow
                </h3>
                <Button
                  onClick={() => setShowWorkflowSelector(!showWorkflowSelector)}
                  variant="outline"
                  size="sm"
                >
                  Change Workflow
                </Button>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Workflow className="w-5 h-5 text-blue-600" />
                    <div>
                      <h4 className="font-semibold text-blue-900">
                        {workflows.find(w => w.id === selectedWorkflow)?.name || "Selected Workflow"}
                      </h4>
                      <p className="text-sm text-blue-700">
                        {workflows.find(w => w.id === selectedWorkflow)?.description || ""}
                      </p>
                    </div>
                  </div>
                  <Badge className="bg-blue-100 text-blue-800">Active</Badge>
                </div>

                {/* Current Approvals */}
                {currentApprovals.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-3 flex items-center gap-2">
                      <Users className="w-4 h-4" />
                      Current Approvals
                    </h4>
                    <div className="space-y-2">
                      {currentApprovals.map((approval) => (
                        <div key={approval.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            {getApprovalStatusIcon(approval.state)}
                            <span className="font-medium">{approval.reviewer}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {getApprovalStatusBadge(approval.state)}
                            {approval.due_at && (
                              <span className="text-xs text-gray-500">
                                Due: {new Date(approval.due_at).toLocaleDateString()}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Workflow Selector */}
              {showWorkflowSelector && (
                <div className="mt-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
                  <h4 className="font-medium mb-3">Select Workflow</h4>
                  <div className="space-y-2">
                    {workflows.map((workflow) => (
                      <div
                        key={workflow.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                          selectedWorkflow === workflow.id
                            ? "border-blue-500 bg-blue-50"
                            : "border-gray-200 bg-white hover:border-gray-300"
                        }`}
                        onClick={() => handleWorkflowChange(workflow.id)}
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h5 className="font-medium text-sm">{workflow.name ?? workflow.id}</h5>
                            <p className="text-xs text-gray-600 mt-1">{workflow.description}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <Badge variant="outline" className="text-xs">
                                {(workflow.steps?.length ?? 0)} steps
                              </Badge>
                              {phaseMap[phase] === (workflow.name ?? workflow.id) && (
                                <Badge className="text-xs bg-green-100 text-green-800">
                                  Suggested
                                </Badge>
                              )}
                            </div>
                          </div>
                          {selectedWorkflow === workflow.id && (
                            <CheckCircle className="w-4 h-4 text-blue-600" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 flex gap-2">
                    <Button
                      onClick={() => setShowWorkflowSelector(false)}
                      variant="outline"
                      size="sm"
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={() => {
                        setSelectedWorkflow("");
                        setShowWorkflowSelector(false);
                      }}
                      variant="outline"
                      size="sm"
                    >
                      Remove Workflow
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          {/* Save Changes Button - Moved to bottom */}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Saving..." : "Save Changes"}
          </Button>
        </form>
      </div>
    </div>
  );
}
