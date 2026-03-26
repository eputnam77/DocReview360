// Progress-related sub-components for the project detail page.
// Extracted from pages/projects/[id]/index.tsx (R-09).

import { cn } from "@/lib/utils";
import React from "react";
import { CheckCircle2 } from "lucide-react";

// ---------------------------------------------------------------------------
// ProgBar
// ---------------------------------------------------------------------------

export function ProgBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
      <div
        className={cn(
          "h-2 rounded-full transition-all",
          pct === 100
            ? "bg-green-500"
            : pct >= 70
              ? "bg-blue-500"
              : pct > 0
                ? "bg-yellow-400"
                : "bg-gray-400",
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// LifecycleStepper
// ---------------------------------------------------------------------------

export const LIFECYCLE_STEPS = [
  { id: "assign_reviewers", label: "Assign Reviewers" },
  { id: "collect_feedback", label: "Collect Feedback" },
  { id: "address_feedback", label: "Address Feedback" },
  { id: "collect_signatures", label: "Collect Signatures" },
  { id: "complete", label: "Complete" },
];

export function LifecycleStepper({ step }: { step: string }) {
  const idx = LIFECYCLE_STEPS.findIndex((s) => s.id === step);
  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-1">
      {LIFECYCLE_STEPS.map((s, i) => {
        const done = i < idx;
        const active = i === idx;
        return (
          <React.Fragment key={s.id}>
            <div className="flex items-center gap-1 flex-shrink-0">
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2",
                  done
                    ? "bg-green-500 border-green-500 text-white"
                    : active
                      ? "bg-indigo-600 border-indigo-600 text-white"
                      : "bg-white border-gray-300 text-gray-400",
                )}
              >
                {done ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
              </div>
              <span
                className={cn(
                  "text-xs font-medium hidden sm:block",
                  active ? "text-indigo-700" : done ? "text-green-600" : "text-gray-400",
                )}
              >
                {s.label}
              </span>
            </div>
            {i < LIFECYCLE_STEPS.length - 1 && (
              <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700 mx-1 min-w-[8px]" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
