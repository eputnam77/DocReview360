export interface StepInstance {
  name: string;
  status: string;
}

export interface WorkflowInstance {
  id: string;
  steps: StepInstance[];
  current: number;
}
