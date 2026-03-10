/**
 * React Query hooks for the projects list and mutations.
 *
 * Centralising project-list fetching here means all pages share the same
 * cache key and benefit from background refetches and optimistic updates
 * without duplicating fetch logic.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import { API, authenticatedFetch } from "./api";

export interface ProjectSummary {
  id: string;
  name: string;
  number: number | null;
  doc_type: string | null;
  status: string;
  phase: string | null;
  current_phase_id: string | null;
  user: string | null;
  org_id: number | null;
  workflow: string | null;
  priority: number;
  created: string;
  updated: string | null;
  reviewers: string[];
}

const PROJECTS_KEY = ["projects"] as const;

/** Fetch all projects visible to the current user. */
export function useProjects() {
  return useQuery<ProjectSummary[]>({
    queryKey: PROJECTS_KEY,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/projects`);
      if (!res.ok) throw new Error(`Failed to fetch projects (${res.status})`);
      return res.json();
    },
  });
}

/** Fetch projects assigned to a specific user. */
export function useUserProjects(username: string | undefined) {
  return useQuery<ProjectSummary[]>({
    queryKey: ["projects", "assigned", username],
    enabled: !!username,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/projects/assigned/${username}`);
      if (!res.ok) throw new Error(`Failed to fetch user projects (${res.status})`);
      return res.json();
    },
  });
}

interface CreateProjectPayload {
  name: string;
  doc_type?: string;
  workflow?: string;
  phase?: string;
  priority?: number;
  description?: string;
  org_id?: number;
}

/** Create a new project and update the projects cache. */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateProjectPayload) => {
      const res = await authenticatedFetch(`${API}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to create project" }));
        throw new Error(err.detail ?? "Failed to create project");
      }
      return res.json() as Promise<ProjectSummary>;
    },
    onSuccess: (newProject) => {
      // Prepend the new project to the cached list
      queryClient.setQueryData(PROJECTS_KEY, (old: ProjectSummary[] | undefined) =>
        old ? [newProject, ...old] : [newProject],
      );
      toast.success("Project created");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });
}

/** Delete a project and remove it from the cache. */
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const res = await authenticatedFetch(`${API}/projects/${projectId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete project");
    },
    onSuccess: (_data, projectId) => {
      queryClient.setQueryData(PROJECTS_KEY, (old: ProjectSummary[] | undefined) =>
        old?.filter((p) => p.id !== projectId) ?? [],
      );
      queryClient.removeQueries({ queryKey: ["project", projectId] });
      toast.success("Project deleted");
    },
    onError: () => {
      toast.error("Failed to delete project");
    },
  });
}
