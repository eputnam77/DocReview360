import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";
import type { Project } from "@/types";

export function useProject(id?: string) {
  return useQuery<Project | null>({
    queryKey: ["project", id],
    enabled: !!id,
    queryFn: async () => {
      const res = await authenticatedFetch(`/projects/${id}`);
      if (!res.ok) {
        throw new Error("Failed to fetch project");
      }
      const proj = await res.json();
      return {
        id: proj.id,
        number: proj.number || 1,
        type: proj.doc_type || "Unknown",
        title: proj.name || "Untitled",
        owner: proj.user || "Unknown",
        status: proj.status || "Draft",
        progress: proj.progress || 0,
        updated: proj.updated || proj.created || new Date().toISOString().split("T")[0],
        editor: "tiptap",
        workflow: proj.workflow,
        currentPhaseId: proj.current_phase_id || proj.phase || null,
        nara_schedule_number: proj.nara_schedule_number ?? null,
        nara_disposition_authority: proj.nara_disposition_authority ?? null,
        nara_retention_period: proj.nara_retention_period ?? null,
        nara_record_series: proj.nara_record_series ?? null,
      } as Project;
    },
  });
}

