import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";
import { toast } from "react-hot-toast";

export interface Comment {
  id: string;
  document: string;
  user: string;
  text: string;
  raw_text: string;
  mentions: string[];
  parent: string | null;
  created: string;
  tags: string[];
  status: "open" | "resolved" | "accepted" | "rejected";
}

interface CreateCommentInput {
  user: string;
  text: string;
  parent?: string;
  tags?: string[];
}

interface UpdateCommentInput {
  status?: Comment["status"];
  text?: string;
  tags?: string[];
}

export function useComments(docId: string | undefined) {
  const queryClient = useQueryClient();
  const queryKey = ["comments", docId];

  const { data: comments = [], isLoading } = useQuery<Comment[]>({
    queryKey,
    enabled: !!docId,
    queryFn: async () => {
      const res = await authenticatedFetch(`/documents/${docId}/comments`);
      if (!res.ok) return [];
      return res.json();
    },
  });

  const createMutation = useMutation({
    mutationFn: async (input: CreateCommentInput) => {
      const res = await authenticatedFetch(`/documents/${docId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? "Failed to post comment");
      }
      return res.json() as Promise<Comment>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ commentId, input }: { commentId: string; input: UpdateCommentInput }) => {
      const res = await authenticatedFetch(
        `/documents/${docId}/comments/${commentId}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? "Failed to update comment");
      }
      return res.json() as Promise<Comment>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  return {
    comments,
    isLoading,
    postComment: (input: CreateCommentInput) => createMutation.mutateAsync(input),
    updateComment: (commentId: string, input: UpdateCommentInput) =>
      updateMutation.mutateAsync({ commentId, input }),
    isPosting: createMutation.isPending,
    isUpdating: updateMutation.isPending,
  };
}
