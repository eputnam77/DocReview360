import React from 'react';
import type { StepInstance } from '@/types';

export function StepStatusBadge({ step }: { step: StepInstance }) {
  return <span className={`badge ${step.status}`} />;
}
