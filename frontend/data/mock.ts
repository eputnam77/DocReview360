import { StepInstance, WorkflowInstance } from "@/types";

export const MOCK_STEPS: StepInstance[] = [
  {
    id: "step1",
    order: 1,
    kind: "Form",
    name: "draft",
    status: "Pending",
    phaseId: "draft",
    required: true,
  },
  {
    id: "step2",
    order: 2,
    kind: "Approval",
    name: "review",
    status: "Pending",
    phaseId: "review",
    required: true,
  },
  {
    id: "step3",
    order: 3,
    kind: "Approval",
    name: "approved",
    status: "Pending",
    phaseId: "approval",
    required: true,
  },
];

export const MOCK_INSTANCE: WorkflowInstance = {
  id: "wf1",
  workflowName: "Sample Workflow",
  requestedBy: { id: "user1", name: "John Doe", avatar: "" },
  startedAt: new Date().toISOString(),
  status: "In-Progress",
  steps: MOCK_STEPS,
  current: 0,
};
