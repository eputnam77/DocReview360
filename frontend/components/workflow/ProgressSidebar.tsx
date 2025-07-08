// components/workflow/ProgressSidebar.tsx
import React from "react";
import type { WorkflowInstance } from "@/types";
import { CheckCircle2, Circle, ClipboardCheck, ThumbsUp } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Shows vertical timeline of workflow steps with current/completed status.
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
  return (
    <aside className="w-72 border-r px-6 py-8 bg-white">
      <h2 className="mb-6 text-lg font-semibold">Progress</h2>
      <ul className="relative space-y-6">
        {/* vertical line for timeline */}
        <span className="absolute left-5 top-10 h-[calc(100%-40px)] w-px bg-border" />
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
                  : "text-muted-foreground"
              )}
              onClick={() => onStepClick?.(i)}
              style={{ cursor: onStepClick ? "pointer" : undefined }}
            >
              {/* Timeline dot/icon */}
              <span className="relative top-2 flex h-5 w-5 items-center justify-center">
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
                <div className="text-sm">
                  {step.name}
                  <span className="ml-2 text-xs uppercase text-muted-foreground">
                    {step.kind}
                  </span>
                </div>
                {/* Optionally: show status */}
                <div className="text-xs text-gray-500">
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
