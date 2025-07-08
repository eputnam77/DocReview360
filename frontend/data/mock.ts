import { StepInstance, WorkflowInstance } from '@/types';

export const MOCK_STEPS: StepInstance[] = [
  { name: 'draft', status: 'pending' },
  { name: 'review', status: 'pending' },
  { name: 'approved', status: 'pending' },
];

export const MOCK_INSTANCE: WorkflowInstance = {
  id: 'wf1',
  steps: MOCK_STEPS,
  current: 0,
};
