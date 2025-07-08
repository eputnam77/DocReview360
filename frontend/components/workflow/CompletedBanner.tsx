import React from 'react';
import type { WorkflowInstance } from '@/types';

export function CompletedBanner({ workflow }: { workflow: WorkflowInstance }) {
  return <div className="completed">{workflow.id}</div>;
}
