import React from 'react';
import { ProgressSidebar, CompletedBanner, StepStatusBadge } from '@/components/workflow';
import { MOCK_INSTANCE } from '@/data/mock';

type Props = { params: { id: string } };

export default function InstancePage({ params }: Props) {
  // Using mock workflow data until API integration lands
  const wf = { ...MOCK_INSTANCE, id: params.id };
  return (
    <div className="flex">
      <ProgressSidebar workflow={wf} />
      <div className="flex-1 p-4 space-y-4">
        <CompletedBanner workflow={wf} />
        <section className="space-y-2">
          {wf.steps.map((step, idx) => (
            <div key={step.name} data-step={step.name} data-active={idx === wf.current} className="flex items-center gap-2">
              <StepStatusBadge step={step} />
              <span>{step.name}</span>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
