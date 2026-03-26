import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";

export interface WorkflowStep {
  name: string;
  status?: "complete" | "active" | "pending";
}

export interface Workflow {
  id: string;
  phase: string;
  steps?: WorkflowStep[];
}

export function usePhases(workflowId?: string) {
  return useQuery<Workflow | null>({
    queryKey: ["phases", workflowId],
    enabled: !!workflowId,
    queryFn: async () => {
      const res = await authenticatedFetch(`/workflows/${workflowId}`);
      if (!res.ok) {
        throw new Error("Failed to fetch workflow");
      }
      const workflow = (await res.json()) as Workflow & { phases?: string[] };
      const phases = Array.isArray(workflow.phases) ? workflow.phases : [];
      const currentIndex = Math.max(phases.indexOf(workflow.phase), 0);
      const steps: WorkflowStep[] = phases.map((phase, index) => ({
        name: phase,
        status:
          index < currentIndex
            ? "complete"
            : index === currentIndex
              ? "active"
              : "pending",
      }));
      return {
        ...workflow,
        steps,
      };
    },
  });
}
