// frontend/components/WorkflowTimeline.tsx
import React from "react";
import { cn } from "@/lib/utils";

export interface TimelineStep {
  name: string;
  status: "complete" | "active" | "upcoming";
  role?: string;
}

interface WorkflowTimelineProps {
  steps: TimelineStep[];
}

export default function WorkflowTimeline({ steps }: WorkflowTimelineProps) {
  if (!steps.length) return null;

  return (
    <nav aria-label="Workflow phases" className="w-full overflow-x-auto">
      <ol className="flex items-center min-w-max">
        {steps.map((step, index) => (
          <React.Fragment key={step.name}>
            <li className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "w-8 h-8 flex items-center justify-center rounded-full border-2 text-xs font-bold transition-colors",
                  step.status === "complete" &&
                    "bg-green-500 border-green-500 text-white",
                  step.status === "active" &&
                    "bg-blue-500 border-blue-500 text-white animate-pulse",
                  step.status === "upcoming" &&
                    "bg-white border-gray-300 text-gray-400 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-500",
                )}
                aria-current={step.status === "active" ? "step" : undefined}
              >
                {step.status === "complete" ? "✓" : index + 1}
              </div>
              <span
                className={cn(
                  "text-xs font-medium whitespace-nowrap max-w-[80px] text-center truncate",
                  step.status === "complete" && "text-green-700 dark:text-green-400",
                  step.status === "active" && "text-blue-700 dark:text-blue-400",
                  step.status === "upcoming" && "text-gray-400 dark:text-gray-500",
                )}
                title={step.name}
              >
                {step.name}
              </span>
              {step.role && (
                <span className="text-[10px] text-gray-400 whitespace-nowrap">{step.role}</span>
              )}
            </li>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-1 min-w-[24px]",
                  step.status === "complete" ? "bg-green-400" : "bg-gray-200 dark:bg-gray-700",
                )}
                aria-hidden="true"
              />
            )}
          </React.Fragment>
        ))}
      </ol>
    </nav>
  );
}
