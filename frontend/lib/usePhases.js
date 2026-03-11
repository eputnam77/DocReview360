import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";
export function usePhases(workflowId) {
    return useQuery({
        queryKey: ["workflow", workflowId],
        enabled: !!workflowId,
        queryFn: async () => {
            const res = await authenticatedFetch(`/workflows/${workflowId}`);
            if (!res.ok) {
                throw new Error("Failed to fetch workflow");
            }
            const workflow = (await res.json());
            const phases = Array.isArray(workflow.phases) ? workflow.phases : [];
            const currentIndex = Math.max(phases.indexOf(workflow.phase), 0);
            const steps = phases.map((phase, index) => ({
                name: phase,
                status: index < currentIndex
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
