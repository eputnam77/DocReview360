import { useQuery } from "@tanstack/react-query";
import { API, authenticatedFetch } from "./api";
export function useProject(id) {
    return useQuery({
        queryKey: ["project", id],
        enabled: !!id,
        queryFn: async () => {
            const res = await authenticatedFetch(`${API}/projects/${id}`);
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
            };
        },
    });
}
