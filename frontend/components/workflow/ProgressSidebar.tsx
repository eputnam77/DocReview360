import React from 'react';
import type { WorkflowInstance } from '@/types';

export function ProgressSidebar({ workflow }: { workflow: WorkflowInstance }) {
  const steps = workflow.steps.map((s) => s.name).join(',');
  return <aside data-steps={steps} data-current={workflow.current} />;
}
