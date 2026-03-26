// Shared types for the project detail page and its sub-components.
// Extracted from pages/projects/[id]/index.tsx (R-09).

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
}

export interface LogEntry {
  id: string;
  timestamp: string;
  action: string;
  type: "approval" | "review" | "edit" | "phase";
  ref?: string;
}

export interface WorkflowStep {
  name: string;
  status?: "complete" | "active" | "pending";
}

export interface Workflow {
  id: string;
  phase: string;
  steps?: WorkflowStep[];
}

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
}

export interface VersionEntry {
  id: string;
  timestamp: string;
  author: string;
  action: string;
}
