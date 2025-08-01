import { StepInstance, WorkflowInstance } from "@/types";

export const MOCK_STEPS: StepInstance[] = [
  { id: "step1", order: 1, kind: "Form", name: "draft", status: "Pending" },
  { id: "step2", order: 2, kind: "Approval", name: "review", status: "Pending" },
  { id: "step3", order: 3, kind: "Approval", name: "approved", status: "Pending" },
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
