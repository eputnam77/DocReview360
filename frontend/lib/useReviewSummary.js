import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";
export function useReviewSummary(projectId, phaseId) {
    return useQuery({
        queryKey: ["review-summary", projectId, phaseId],
        enabled: !!projectId,
        queryFn: async () => {
            const phaseParam = phaseId ? `?phase=${encodeURIComponent(phaseId)}` : "";
            const res = await authenticatedFetch(`/projects/${projectId}/reviews${phaseParam}`);
            if (!res.ok) {
                throw new Error("Failed to fetch reviews");
            }
            const data = await res.json();
            return { count: Array.isArray(data) ? data.length : 0 };
        },
    });
}
