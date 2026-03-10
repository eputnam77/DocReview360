/**
 * React Query hooks for document fetching and mutations.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import { API, authenticatedFetch } from "./api";

export interface DocumentSummary {
  id: string;
  project: string | null;
  user: string | null;
  content: string;
  priority: number;
  created: string;
  version_number?: number;
  frozen?: boolean;
  quality_score?: number | null;
  plain_language_grade?: string | null;
}

export const documentKeys = {
  all: ["documents"] as const,
  byProject: (projectId: string) => ["documents", "project", projectId] as const,
  byId: (docId: string) => ["document", docId] as const,
  versions: (docId: string) => ["document", docId, "versions"] as const,
};

/** Fetch all documents for a project. */
export function useProjectDocuments(projectId: string | undefined) {
  return useQuery<DocumentSummary[]>({
    queryKey: projectId ? documentKeys.byProject(projectId) : documentKeys.all,
    enabled: !!projectId,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/documents?project=${projectId}`);
      if (!res.ok) throw new Error(`Failed to fetch documents (${res.status})`);
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    },
  });
}

/** Fetch a single document by ID. */
export function useDocument(docId: string | undefined) {
  return useQuery<DocumentSummary>({
    queryKey: docId ? documentKeys.byId(docId) : documentKeys.all,
    enabled: !!docId,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/documents/${docId}`);
      if (!res.ok) throw new Error(`Failed to fetch document (${res.status})`);
      return res.json();
    },
  });
}

/** Fetch version history for a document. */
export function useDocumentVersions(docId: string | undefined) {
  return useQuery({
    queryKey: docId ? documentKeys.versions(docId) : documentKeys.all,
    enabled: !!docId,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/documents/${docId}/versions`);
      if (!res.ok) throw new Error("Failed to fetch document versions");
      return res.json();
    },
  });
}

/** Update document content with optimistic update. */
export function useUpdateDocument(docId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (content: string) => {
      const res = await authenticatedFetch(`${API}/documents/${docId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error("Failed to update document");
      return res.json() as Promise<DocumentSummary>;
    },
    onMutate: async (content: string) => {
      await queryClient.cancelQueries({ queryKey: documentKeys.byId(docId) });
      const previous = queryClient.getQueryData(documentKeys.byId(docId));
      queryClient.setQueryData(documentKeys.byId(docId), (old: DocumentSummary | undefined) =>
        old ? { ...old, content } : old,
      );
      return { previous };
    },
    onError: (_err, _content, context) => {
      queryClient.setQueryData(documentKeys.byId(docId), context?.previous);
      toast.error("Failed to save document");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.byId(docId) });
    },
  });
}

/** Delete a document. */
export function useDeleteDocument(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (docId: string) => {
      const res = await authenticatedFetch(`${API}/documents/${docId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete document");
    },
    onSuccess: (_data, docId) => {
      queryClient.removeQueries({ queryKey: documentKeys.byId(docId) });
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: documentKeys.byProject(projectId) });
      }
      toast.success("Document deleted");
    },
    onError: () => {
      toast.error("Failed to delete document");
    },
  });
}
