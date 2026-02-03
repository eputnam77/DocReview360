import type { WorkflowInstance } from "@/types";

export const MOCK_INSTANCE: WorkflowInstance = {
  id: "wf1",
  workflowName: "Project Phoenix Review",
  requestedBy: {
    id: "u1",
    name: "A. Smith",
    avatar: "/avatars/alice.png",
  },
  startedAt: "2024-06-01T00:00:00Z",
  status: "In-Progress",
  current: 1,
  steps: [
    {
      id: "step-1",
      order: 1,
      kind: "Form",
      name: "Draft Submission",
      status: "Completed",
      completedAt: "2024-06-01T01:00:00Z",
      completedBy: {
        id: "u2",
        name: "Reviewer One",
        avatar: "/avatars/reviewer1.png",
      },
    },
    {
      id: "step-2",
      order: 2,
      kind: "Approval",
      name: "SME Review",
      status: "Pending",
      required: true,
      phaseId: "phase-1",
    },
    {
      id: "step-3",
      order: 3,
      kind: "Approval",
      name: "Final Sign-off",
      status: "Pending",
      required: true,
      phaseId: "phase-2",
    },
  ],
};
