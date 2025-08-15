// frontend/components/workflow/ProgressSidebar.tsx

import React from "react";
import type { WorkflowInstance } from "@/types";
import { CheckCircle2, Circle, ClipboardCheck, ThumbsUp } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Shows a vertical timeline of workflow steps with current/completed status.
 * @param workflow - The workflow instance to show progress for.
 * @param onStepClick - Optional callback when a step is clicked.
 */
interface ProgressSidebarProps {
  workflow: WorkflowInstance;
  onStepClick?: (stepIndex: number) => void;
}

const ProgressSidebar: React.FC<ProgressSidebarProps> = ({
  workflow,
  onStepClick,
}) => {
  const completed = workflow.steps.filter((_, i) => i < workflow.current).length;
  const total = workflow.steps.length;
  const progress = total ? Math.round((completed / total) * 100) : 0;
  return (
    <aside
      className="w-72 border-r px-6 py-8 bg-white dark:bg-gray-950"
      aria-label="Workflow Progress"
    >
      <h2 className="mb-6 text-lg font-semibold">Progress</h2>
      <div className="mb-6">
        <div className="flex justify-between text-xs">
          <span>
            {completed} of {total} steps
          </span>
          <span>{progress}%</span>
        </div>
        <div className="mt-1 h-2 w-full rounded bg-muted">
          <div
            className="h-2 rounded bg-purple-600"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <ul className="relative space-y-6">
        {/* vertical line for timeline */}
        <span
          className="absolute left-5 top-10 h-[calc(100%-40px)] w-px bg-border"
          aria-hidden="true"
        />
        {workflow.steps.map((step, i) => {
          const isCompleted = i < workflow.current;
          const isCurrent = i === workflow.current;
          return (
            <li
              key={step.name + i}
              className={cn(
                "relative flex items-start gap-3 rounded-lg px-2 py-2 transition-colors",
                isCurrent
                  ? "bg-purple-50 font-bold"
                  : isCompleted
                    ? "text-gray-700"
                    : "text-muted-foreground",
              )}
              onClick={() => onStepClick?.(i)}
              style={{ cursor: onStepClick ? "pointer" : undefined }}
              aria-current={isCurrent ? "step" : undefined}
            >
              {/* Timeline dot/icon */}
              <span
                className="relative top-2 flex h-5 w-5 items-center justify-center"
                aria-hidden="true"
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : isCurrent ? (
                  <Circle className="h-5 w-5 text-purple-600" />
                ) : step.kind === "Form" ? (
                  <ClipboardCheck className="h-5 w-5 text-gray-400" />
                ) : (
                  <ThumbsUp className="h-5 w-5 text-gray-400" />
                )}
              </span>
              {/* Step info */}
              <div>
                <div className="text-sm flex gap-2 items-center">
                  {step.name}
                  <span className="ml-2 text-xs uppercase text-muted-foreground">
                    {step.kind}
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {isCompleted
                    ? "Completed"
                    : isCurrent
                      ? "In Progress"
                      : "Pending"}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </aside>
  );
};

export default ProgressSidebar;
