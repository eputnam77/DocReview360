import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API, authenticatedFetch } from "./api";
import { toast } from "react-hot-toast";
export function useProjectReviewers(projectId) {
    const queryClient = useQueryClient();
    const queryKey = ["project-reviewers", projectId];
    const query = useQuery({
        queryKey,
        enabled: !!projectId,
        queryFn: async () => {
            if (!projectId)
                return [];
            const res = await authenticatedFetch(`${API}/projects/${projectId}/reviewers`);
            if (!res.ok)
                throw new Error("Failed to fetch reviewers");
            const data = await res.json();
            return Array.isArray(data) ? data : [];
        },
    });
    const addReviewerMutation = useMutation({
        mutationFn: async (reviewer) => {
            const res = await authenticatedFetch(`${API}/projects/${projectId}/reviewers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reviewer }),
            });
            if (!res.ok)
                throw new Error("Failed to add reviewer");
            return res.json();
        },
        onMutate: async (reviewer) => {
            await queryClient.cancelQueries({ queryKey });
            const previous = queryClient.getQueryData(queryKey) ?? [];
            if (!previous.includes(reviewer)) {
                queryClient.setQueryData(queryKey, [...previous, reviewer]);
            }
            return { previous };
        },
        onError: (_err, _reviewer, context) => {
            queryClient.setQueryData(queryKey, context?.previous);
            toast.error("Failed to add reviewer");
        },
        onSuccess: (data) => {
            queryClient.setQueryData(queryKey, Array.isArray(data) ? data : []);
            toast.success("Reviewer added");
        },
    });
    const updateReviewerMutation = useMutation({
        mutationFn: async ({ reviewer, nextReviewer, }) => {
            const res = await authenticatedFetch(`${API}/projects/${projectId}/reviewers/${encodeURIComponent(reviewer)}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reviewer: nextReviewer }),
            });
            if (!res.ok)
                throw new Error("Failed to update reviewer");
            return res.json();
        },
        onMutate: async ({ reviewer, nextReviewer }) => {
            await queryClient.cancelQueries({ queryKey });
            const previous = queryClient.getQueryData(queryKey) ?? [];
            const updated = previous.map((value) => value === reviewer ? nextReviewer : value);
            queryClient.setQueryData(queryKey, Array.from(new Set(updated)));
            return { previous };
        },
        onError: (_err, _data, context) => {
            queryClient.setQueryData(queryKey, context?.previous);
            toast.error("Failed to update reviewer");
        },
        onSuccess: (data) => {
            queryClient.setQueryData(queryKey, Array.isArray(data) ? data : []);
            toast.success("Reviewer updated");
        },
    });
    const removeReviewerMutation = useMutation({
        mutationFn: async (reviewer) => {
            const res = await authenticatedFetch(`${API}/projects/${projectId}/reviewers/${encodeURIComponent(reviewer)}`, {
                method: "DELETE",
            });
            if (!res.ok)
                throw new Error("Failed to remove reviewer");
            return res.json();
        },
        onMutate: async (reviewer) => {
            await queryClient.cancelQueries({ queryKey });
            const previous = queryClient.getQueryData(queryKey) ?? [];
            queryClient.setQueryData(queryKey, previous.filter((value) => value !== reviewer));
            return { previous };
        },
        onError: (_err, _reviewer, context) => {
            queryClient.setQueryData(queryKey, context?.previous);
            toast.error("Failed to remove reviewer");
        },
        onSuccess: (data) => {
            queryClient.setQueryData(queryKey, Array.isArray(data) ? data : []);
            toast.success("Reviewer removed");
        },
    });
    return {
        reviewers: query.data ?? [],
        isLoading: query.isLoading,
        error: query.error,
        addReviewer: addReviewerMutation.mutateAsync,
        updateReviewer: updateReviewerMutation.mutateAsync,
        removeReviewer: removeReviewerMutation.mutateAsync,
    };
}
