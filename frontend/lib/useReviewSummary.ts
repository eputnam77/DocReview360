import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";
import type { ReviewSummary } from "@/types";

export function useReviewSummary(projectId?: string, phaseId?: string) {
  return useQuery<ReviewSummary>({
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

