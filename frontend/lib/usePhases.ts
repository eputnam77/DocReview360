import { useQuery } from "@tanstack/react-query";
import { API, authenticatedFetch } from "./api";

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
    queryKey: ["workflow", workflowId],
    enabled: !!workflowId,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/workflows/${workflowId}`);
      if (!res.ok) {
        throw new Error("Failed to fetch workflow");
      }
      return (await res.json()) as Workflow;
    },
  });
}

