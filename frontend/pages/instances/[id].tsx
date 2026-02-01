import {
  CompletedBanner,
  ProgressSidebar,
  StepStatusBadge,
} from "@/components/workflow";
import { useWorkflowInstance } from "@/lib/useWorkflowInstance";
import { useRouter } from "next/router";

export default function InstancePage() {
  const router = useRouter();
  const id = typeof router.query.id === "string" ? router.query.id : undefined;
  const { data: wf, isLoading, error } = useWorkflowInstance(id);

  if (!id) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <p className="text-sm text-muted-foreground">Loading workflow...</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <p className="text-sm text-muted-foreground">Loading workflow...</p>
      </div>
    );
  }

  if (error || !wf) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <p className="text-sm text-red-600">Unable to load workflow.</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Sidebar with progress */}
      <ProgressSidebar workflow={wf} />

      <div className="flex-1 p-6 space-y-6">
        {/* Completed Banner or summary */}
        <CompletedBanner
          workflowName={wf.workflowName}
          completedAt={wf.steps.find((s) => s.status === "Completed")?.completedAt}
        />

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
