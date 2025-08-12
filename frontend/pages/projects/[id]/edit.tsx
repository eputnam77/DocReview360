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
import { getDemoProject } from "@/data/demoProjects";
import { API } from "@/lib/api";
import { CheckCircle, Clock, Users, Workflow, XCircle } from "lucide-react";
import { useRouter } from "next/router";
import React, { useEffect, useRef, useState } from "react";

const DOCUMENT_TYPES: string[] = [];

const DEMO_PHASES: string[] = [];
const DEMO_WORKFLOWS: string[] = [];

interface Workflow {
  id: string;
  name: string;
  description?: string;
  phases: string[];
  reviewers: string[];
}

interface Approval {
  id: string;
  reviewer: string;
  state: "pending" | "approved" | "rejected";
  due_at?: string;
  signed_at?: string;
}

const DEMO_WORKFLOWS_DATA: Workflow[] = [
  {
    id: "branch-coordination",
    name: "branch-coordination",
    description:
      "Standard workflow with SME, Front Line Manager, Product Policy Manager, Technical Writer, Senior Technical Writer, and Technical Writing Manager steps",
    phases: ["Internal FAA Review", "Public Comment", "Final Issuance"],
    reviewers: [],
  },
];

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
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [workflowNames, setWorkflowNames] = useState<string[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("");
  const [currentApprovals, setCurrentApprovals] = useState<Approval[]>([]);
  const [showWorkflowSelector, setShowWorkflowSelector] = useState(false);
  const [phases, setPhases] = useState<string[]>(DEMO_PHASES);
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [phaseMap, setPhaseMap] = useState<Record<string, string>>({});

  const manualWorkflow = useRef(false);

  // Load phase-workflow mapping from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("phaseWorkflowMap");
    if (saved) {
      try {
        setPhaseMap(JSON.parse(saved));
      } catch {
        // ignore parse errors
      }
    }
  }, []);

  // Reset manual workflow flag when phase changes
  useEffect(() => {
    manualWorkflow.current = false;
  }, [docType, phase]);

  // Auto-select workflow based on phase mapping
  useEffect(() => {
    if (!manualWorkflow.current && phase) {
      const def = phaseMap[phase];
      if (def) {
        // Find the workflow ID that matches the mapped workflow name
        const mappedWorkflow = workflows.find(w => w.name === def);
        if (mappedWorkflow) {
          setSelectedWorkflow(mappedWorkflow.id);
        }
      }
    }
  }, [phase, phaseMap, workflows]);

  // Fetch project details and available workflows on mount
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    console.log('Edit page: Fetching project data from:', `${API}/projects/${id}`);

    // Fetch project data
    fetch(`${API}/projects/${id}`)
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
            const wfRes = await fetch(`${API}/workflows/${proj.workflow}`);
            if (wfRes.ok) {
              const workflow = await wfRes.json();
              setSelectedWorkflow(workflow.id);
            }
          } catch (error) {
            console.error('Failed to fetch workflow:', error);
          }

          // Fetch approvals for the workflow
          try {
            const apRes = await fetch(`${API}/approvals?workflow=${proj.workflow}`);
            if (apRes.ok) {
              const approvals = await apRes.json();
              setCurrentApprovals(approvals);
            }
          } catch (error) {
            console.error('Failed to fetch approvals:', error);
          }
        } else {
          // If no workflow is associated, try to find workflow by project ID
          try {
            const wfRes = await fetch(`${API}/workflows?project=${id}`);
            if (wfRes.ok) {
              const workflows = await wfRes.json();
              if (workflows.length > 0) {
                const projectWorkflow = workflows[0];
                setSelectedWorkflow(projectWorkflow.id);

                // Fetch approvals for this workflow
                const apRes = await fetch(`${API}/approvals?workflow=${projectWorkflow.id}`);
                if (apRes.ok) {
                  const approvals = await apRes.json();
                  setCurrentApprovals(approvals);
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
        console.log('Edit page: Falling back to demo data');
        const demo = getDemoProject(String(id));
        if (demo) {
          setDocId(String(demo.number)); // Use number as docId for demo
          setDocNumber(String(demo.number)); // Document number, ensure it's a string
          setTitle(demo.title);
          setSme(demo.user || "");
          setDocType(demo.type);
          // Set phase to first available phase from API, or empty if none available
          setPhase(phases.length > 0 ? phases[0] : "");
          setDescription(demo.title);
        } else {
          setError("Could not load project.");
        }
        setLoading(false);
      });

    // Fetch available workflows (instances). If none, fall back to default template
    fetch(`${API}/workflows`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Workflow[]) => {
        const list = (Array.isArray(data) && data.length) ? data : DEMO_WORKFLOWS_DATA;
        setWorkflows(list);
        setWorkflowNames(list.map((w) => w.name));
      })
      .catch(() => {
        setWorkflows(DEMO_WORKFLOWS_DATA);
        setWorkflowNames(DEMO_WORKFLOWS_DATA.map((w) => w.name));
      });

    // Fetch available phases
    fetch(`${API}/phases`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        const phaseNames = data.length
          ? data.map((d: any) => (typeof d === "string" ? d : d.name))
          : DEMO_PHASES;
        setPhases(phaseNames);
      })
      .catch(() => {
        setPhases(DEMO_PHASES);
      });

    // Fetch available document types
    fetch(`${API}/document-types`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        const docTypeNames = data.length
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

    const formData = new FormData();
    formData.append("number", String(docNumber)); // Ensure it's a string
    formData.append("name", title);
    formData.append("user", sme);
    formData.append("doc_type", docType);
    formData.append("phase", phase);
    formData.append("description", description);

    try {
      const res = await fetch(`${API}/projects/${id}`, {
        method: "PUT",
        body: formData,
      });
      if (!res.ok) throw new Error("Failed to update project");

      // If a workflow is selected, update the project's workflow association
      if (selectedWorkflow) {
        const selectedWf = workflows.find(w => w.id === selectedWorkflow);
        if (selectedWf) {
          try {
            // Update the project to associate it with the selected workflow
            const projectUpdateRes = await fetch(`${API}/projects/${id}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                workflow: selectedWf.id
              })
            });

            if (!projectUpdateRes.ok) {
              console.error('Failed to update project workflow association');
            }

            // Check if workflow already exists for this project
            const existingWorkflowRes = await fetch(`${API}/workflows?project=${id}`);
            let existingWorkflow = null;
            if (existingWorkflowRes.ok) {
              const workflows = await existingWorkflowRes.json();
              existingWorkflow = workflows.find((w: any) => w.project === id);
            }

            if (!existingWorkflow) {
              // Create new workflow for the project if none exists
              const wfRes = await fetch(`${API}/workflows`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  project: id,
                  phases: selectedWf.phases
                })
              });

              if (wfRes.ok) {
                const newWorkflow = await wfRes.json();

                // Create approvals for each reviewer
                for (const reviewer of selectedWf.reviewers) {
                  await fetch(`${API}/approvals`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      workflow: newWorkflow.id,
                      reviewer: reviewer
                    })
                  });
                }
              }
            } else {
              // Update existing workflow with new phases and reviewers
              const wfUpdateRes = await fetch(`${API}/workflows/${existingWorkflow.id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  phases: selectedWf.phases
                })
              });

              if (wfUpdateRes.ok) {
                // Clear existing approvals and create new ones
                const existingApprovalsRes = await fetch(`${API}/approvals?workflow=${existingWorkflow.id}`);
                if (existingApprovalsRes.ok) {
                  const existingApprovals = await existingApprovalsRes.json();
                  for (const approval of existingApprovals) {
                    await fetch(`${API}/approvals/${approval.id}`, {
                      method: "DELETE"
                    });
                  }
                }

                // Create new approvals for each reviewer
                for (const reviewer of selectedWf.reviewers) {
                  await fetch(`${API}/approvals`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      workflow: existingWorkflow.id,
                      reviewer: reviewer
                    })
                  });
                }
              }
            }
          } catch (error) {
            console.error('Failed to update workflow:', error);
            // Don't fail the entire update if workflow creation fails
          }
        }
      }

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
                  {workflows.map((w) => (
                    <SelectItem key={w.id} value={w.id}>
                      <div className="flex items-center justify-between w-full">
                        <span>{w.name}</span>
                        {phaseMap[phase] === w.name && (
                          <Badge variant="outline" className="ml-2 text-xs">
                            Suggested
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {phaseMap[phase] && (
                <p className="text-xs text-gray-500 mt-1">
                  Suggested workflow for "{phase}" phase
                </p>
              )}
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
                            <h5 className="font-medium text-sm">{workflow.name}</h5>
                            <p className="text-xs text-gray-600 mt-1">{workflow.description}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <Badge variant="outline" className="text-xs">
                                {workflow.phases.length} phases
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {workflow.reviewers.length} reviewers
                              </Badge>
                              {phaseMap[phase] === workflow.name && (
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
