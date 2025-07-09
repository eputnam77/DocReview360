// frontend/app/instances/[id]/page.tsx
import React from "react";
import {
  ProgressSidebar,
  CompletedBanner,
  StepStatusBadge,
} from "@/components/workflow";
import { MOCK_INSTANCE } from "@/data/mock";

// Type for Next.js dynamic route params
type Props = { params: { id: string } };

export default function InstancePage({ params }: Props) {
  // Using mock workflow data until API integration lands
  const wf = { ...MOCK_INSTANCE, id: params.id };

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Sidebar with progress */}
      <ProgressSidebar workflow={wf} />

      <div className="flex-1 p-6 space-y-6">
        {/* Completed Banner or summary */}
        <CompletedBanner workflow={wf} />

        {/* Steps Progress */}
        <section className="space-y-4">
          {wf.steps.map((step, idx) => (
            <div
              key={step.name}
              data-step={step.name}
              data-active={idx === wf.current}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border transition 
                ${
                  idx === wf.current
                    ? "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/30"
                    : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800"
                }`}
            >
              <StepStatusBadge step={step} />
              <span
                className={`font-medium ${
                  idx === wf.current
                    ? "text-indigo-700 dark:text-indigo-300"
                    : "text-gray-700 dark:text-gray-200"
                }`}
              >
                {step.name}
              </span>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
