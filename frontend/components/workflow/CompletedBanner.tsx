// components/workflow/CompletedBanner.tsx
import React from "react";
import { Rocket } from "lucide-react";

interface CompletedBannerProps {
  workflowName?: string;
  completedAt?: string; // ISO string, optional
}

/**
 * Big purple rocket gradient banner to show workflow completion!
 * Optionally pass workflowName and completedAt to show extra info.
 */
const CompletedBanner: React.FC<CompletedBannerProps> = ({
  workflowName,
  completedAt,
}) => {
  // Format completion date if provided
  let completedText = "";
  if (workflowName && completedAt) {
    completedText = `${workflowName} – ${new Date(completedAt).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    })}`;
  }

  return (
    <div className="rounded-lg bg-gradient-to-r from-purple-600 to-purple-400 p-10 text-center text-white shadow-lg">
      <Rocket className="mx-auto mb-4 h-10 w-10" />
      <h3 className="text-xl font-semibold">
        This workflow instance is complete!
      </h3>
      {completedText && (
        <p className="mt-2 text-sm text-purple-100">{completedText}</p>
      )}
    </div>
  );
};

export default CompletedBanner;
