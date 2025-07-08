// frontend/types.ts

/** Type for workflow step kind */
export type StepKind = "Form" | "Approval";

/** Type for workflow step status */
export type StepStatus = "Completed" | "Pending" | "Rejected";

/** One step inside a workflow run ("instance") */
export interface StepInstance {
  id: string;                // unique step-run id
  order: number;             // 1-based position
  kind: StepKind;            // Form | Approval
  name: string;              // e.g. "VP Demand Gen"
  status: StepStatus;        // current state
  completedAt?: string;      // ISO if done
  completedBy?: {            // user info if done
    id: string;
    name: string;
    avatar: string;
  };
}

/** A single execution of a workflow template */
export interface WorkflowInstance {
  id: string;                // instance id
  workflowName: string;      // template title
  requestedBy: { id: string; name: string; avatar: string };
  startedAt: string;         // ISO
  status: "Completed" | "In-Progress";
  steps: StepInstance[];
  current: number;           // index of active step (0-based)
}
