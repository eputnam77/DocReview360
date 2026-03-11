// frontend/types.ts

/** Type for workflow step kind */
export type StepKind = "Form" | "Approval";

/** Type for workflow step status */
export type StepStatus = "Completed" | "Pending" | "Rejected";

/** One step inside a workflow run ("instance") */
export interface StepInstance {
  id: string; // unique step-run id
  order: number; // 1-based position
  kind: StepKind; // Form | Approval
  name: string; // e.g. "VP Demand Gen"
  status: StepStatus; // current state
  phaseId?: string; // workflow phase identifier
  required?: boolean; // whether the step is mandatory
  completedAt?: string; // ISO if done
  completedBy?: {
    // user info if done
    id: string;
    name: string;
    avatar: string;
  };
}

/** A single execution of a workflow template */
export interface WorkflowInstance {
  id: string; // instance id
  workflowName: string; // template title
  requestedBy: { id: string; name: string; avatar: string };
  startedAt: string; // ISO
  status: "Completed" | "In-Progress";
  steps: StepInstance[];
  current: number; // index of active step (0-based)
}

/** Categories shown in the workflow gallery */
export type Category = "All" | "Compliance" | "HR" | "General";

import type { ReactNode } from "react";

/** Template metadata for the gallery */
export interface Template {
  id: string;
  title: string;
  description: string;
  category: Category;
  icon: ReactNode;
}

/** Basic phase information */
export interface Phase {
  id: string;
  name: string;
  dueAt?: string;
}

/** Core project metadata shared across views */
export interface Project {
  id: string;
  number: string | number;
  type: string;
  title: string;
  owner: string;
  status: string;
  progress: number;
  updated?: string;
  editor?: string;
  workflow?: string;
  currentPhaseId?: string | null;
  // NARA records management fields
  nara_schedule_number?: string | null;
  nara_disposition_authority?: string | null;
  nara_retention_period?: string | null;
  nara_record_series?: string | null;
}

/** Approval information for workflow steps */
export interface Approval {
  id: string;
  reviewer: string;
  email: string;
  state: "pending" | "approved" | "overdue" | "rejected";
  dueAt: string;
  signedAt?: string;
  comments?: string;
  documensoSigId?: string;
  description?: string;
  phaseId?: string;
  required?: boolean;
  signature_provider?: string;
  signature_id?: string;
  certificate_url?: string;
}

/** Summary of reviews for a given phase */
export interface ReviewSummary {
  count: number;
}
