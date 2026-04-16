import { useCallback, useState } from "react";
import { toast } from "react-hot-toast";
import { authenticatedFetch } from "@/lib/api";
import type { Workflow } from "@/components/project/_types";
import { useQueryClient } from "@tanstack/react-query";

export interface PhaseManagementState {
  showPhaseDialog: boolean;
  setShowPhaseDialog: React.Dispatch<React.SetStateAction<boolean>>;
  pendingPhase: string | null;
  requestPhaseChange: (phaseId: string) => void;
  confirmPhaseChange: () => Promise<void>;
}

export function usePhaseManagement({
  id,
  project,
  workflow,
  canAdvance,
  setProject,
  setWorkflow,
}: {
  id: string | undefined;
  project: { id: string; currentPhaseId?: string | null; workflow?: string | null } | null;
  workflow: Workflow | null;
  canAdvance: boolean;
  setProject: React.Dispatch<React.SetStateAction<any>>;
  setWorkflow: React.Dispatch<React.SetStateAction<Workflow | null>>;
}): PhaseManagementState {
  const queryClient = useQueryClient();
  const [showPhaseDialog, setShowPhaseDialog] = useState(false);
  const [pendingPhase, setPendingPhase] = useState<string | null>(null);

  const handlePhaseChange = useCallback(
    (phaseId: string) => {
      if (!workflow?.steps) return;
      const idx = workflow.steps.findIndex((s) => s.name === phaseId);
      if (idx === -1) return;
      const steps = workflow.steps.map((s, i) => ({
        ...s,
        status:
          i < idx ? ("complete" as const) : i === idx ? ("active" as const) : ("pending" as const),
      }));
      setWorkflow({ ...workflow, steps, phase: steps[idx].name });
      setProject((prev: any) => (prev ? { ...prev, currentPhaseId: steps[idx].name } : prev));
    },
    [workflow, setProject, setWorkflow],
  );

  const requestPhaseChange = useCallback(
    (phaseId: string) => {
      if (phaseId === project?.currentPhaseId) return;
      if (!canAdvance) {
        toast.error("All required approvals must be complete before advancing the phase.");
        return;
      }
      setPendingPhase(phaseId);
      setShowPhaseDialog(true);
    },
    [project?.currentPhaseId, canAdvance],
  );

  const confirmPhaseChange = useCallback(async () => {
    if (pendingPhase && project?.id) {
      try {
        const res = await authenticatedFetch(`/projects/${project.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phase: pendingPhase }),
        });
        if (!res.ok) throw new Error("Failed to update project phase");
        handlePhaseChange(pendingPhase);
        queryClient.invalidateQueries({ queryKey: ["project", project.id] });
        if (project.workflow) {
          queryClient.invalidateQueries({ queryKey: ["workflow", project.workflow] });
        }
      } catch (error) {
        console.warn("[usePhaseManagement]", error);
        toast.error("Failed to update phase");
      }
    }
    setShowPhaseDialog(false);
    setPendingPhase(null);
  }, [pendingPhase, project, handlePhaseChange, queryClient]);

  return { showPhaseDialog, setShowPhaseDialog, pendingPhase, requestPhaseChange, confirmPhaseChange };
}
