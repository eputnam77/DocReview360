import { useCallback, useState } from "react";
import { toast } from "react-hot-toast";
import { authenticatedFetch } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import type { Approval } from "@/components/project/_types";

export interface ReviewerManagementState {
  reviewerInput: string;
  setReviewerInput: React.Dispatch<React.SetStateAction<string>>;
  reviewerActionError: string | null;
  setReviewerActionError: React.Dispatch<React.SetStateAction<string | null>>;
  addingReviewer: boolean;
  approvalReviewerInput: string;
  setApprovalReviewerInput: React.Dispatch<React.SetStateAction<string>>;
  approvalActionError: string | null;
  setApprovalActionError: React.Dispatch<React.SetStateAction<string | null>>;
  addingApproval: boolean;
  editingReviewer: string | null;
  setEditingReviewer: React.Dispatch<React.SetStateAction<string | null>>;
  editingValue: string;
  setEditingValue: React.Dispatch<React.SetStateAction<string>>;
  refreshReviewerData: () => void;
  createApprovalForReviewer: (reviewer: string) => Promise<boolean>;
  handleAddReviewer: () => Promise<void>;
  handleAddApproval: () => Promise<void>;
  handleAssignApproval: (approvalId: string, reviewer: string) => Promise<void>;
  handleUpdateReviewer: () => Promise<void>;
  handleRemoveReviewer: (reviewer: string) => Promise<void>;
}

export function useReviewerManagement({
  id,
  project,
  workflow,
  approvals,
  setApprovals,
  approvalReviewerOptions,
  reviewerOptions,
  addReviewer,
  updateReviewer,
  removeReviewer,
}: {
  id: string | undefined;
  project: { id: string; currentPhaseId?: string | null; workflow?: string | null } | null;
  workflow: { phase?: string | null } | null;
  approvals: Approval[];
  setApprovals: React.Dispatch<React.SetStateAction<Approval[]>>;
  approvalReviewerOptions: string[];
  reviewerOptions: string[];
  addReviewer: (reviewer: string) => Promise<void>;
  updateReviewer: (args: { reviewer: string; nextReviewer: string }) => Promise<void>;
  removeReviewer: (reviewer: string) => Promise<void>;
}): ReviewerManagementState {
  const queryClient = useQueryClient();
  const [reviewerInput, setReviewerInput] = useState("");
  const [reviewerActionError, setReviewerActionError] = useState<string | null>(null);
  const [addingReviewer, setAddingReviewer] = useState(false);
  const [approvalReviewerInput, setApprovalReviewerInput] = useState("");
  const [approvalActionError, setApprovalActionError] = useState<string | null>(null);
  const [addingApproval, setAddingApproval] = useState(false);
  const [editingReviewer, setEditingReviewer] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");

  const refreshReviewerData = useCallback(() => {
    if (!project?.id) return;
    queryClient.invalidateQueries({ queryKey: ["project", project.id] });
    queryClient.invalidateQueries({ queryKey: ["project-reviewers", project.id] });
    if (project.workflow) {
      queryClient.invalidateQueries({ queryKey: ["approvals", project.workflow] });
      queryClient.invalidateQueries({ queryKey: ["workflow", project.workflow] });
    }
  }, [project?.id, project?.workflow, queryClient]);

  const createApprovalForReviewer = useCallback(
    async (reviewer: string): Promise<boolean> => {
      if (!project?.workflow) throw new Error("This project has no workflow configured.");
      const phaseId = project.currentPhaseId ?? workflow?.phase ?? undefined;
      const alreadyExists = approvals.some(
        (a) =>
          a.reviewer === reviewer &&
          ((phaseId && a.phaseId === phaseId) || (!phaseId && !a.phaseId)),
      );
      if (alreadyExists) return false;

      const response = await authenticatedFetch("/approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow: project.workflow,
          reviewer,
          phase_id: phaseId,
          required: true,
          description: "Review Approval",
        }),
      });
      if (!response.ok) {
        let detail = "Failed to create approval";
        try {
          const data = await response.json();
          if (typeof data?.detail === "string" && data.detail.trim()) detail = data.detail;
        } catch { /* ignore */ }
        throw new Error(detail);
      }
      const created = await response.json();
      if (!created?.id || !created?.reviewer) {
        throw new Error("Unexpected response shape from POST /approvals — missing id or reviewer");
      }
      setApprovals((prev) => [
        {
          id: created.id,
          reviewer: created.reviewer,
          email: created.reviewer,
          state: created.state,
          dueAt: created.due_at || new Date().toISOString().split("T")[0],
          signedAt: created.signed_at,
          comments: created.comments || "",
          documensoSigId: created.signature || created.signature_id,
          description: created.description,
          phaseId: created.phase_id,
          required: created.required,
          role: created.role,
        },
        ...prev,
      ]);
      refreshReviewerData();
      return true;
    },
    [approvals, project?.currentPhaseId, project?.workflow, refreshReviewerData, workflow?.phase, setApprovals],
  );

  const handleAddReviewer = useCallback(async () => {
    const reviewer = reviewerInput.trim();
    if (!reviewer) {
      const message = "Select a reviewer to add.";
      setReviewerActionError(message);
      toast.error(message);
      return;
    }
    if (reviewerOptions.length > 0 && !reviewerOptions.includes(reviewer)) {
      const message = "Reviewer must be an existing reviewer username.";
      setReviewerActionError(message);
      toast.error(message);
      return;
    }
    try {
      setAddingReviewer(true);
      setReviewerActionError(null);
      await addReviewer(reviewer);
      const created = await createApprovalForReviewer(reviewer);
      setReviewerInput("");
      if (!created) toast("Reviewer added. Approval already exists for this phase.");
      refreshReviewerData();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to add reviewer";
      setReviewerActionError(message);
    } finally {
      setAddingReviewer(false);
    }
  }, [addReviewer, createApprovalForReviewer, reviewerInput, reviewerOptions, refreshReviewerData]);

  const handleAddApproval = useCallback(async () => {
    const reviewer = approvalReviewerInput.trim();
    if (!reviewer) {
      const message = "Select a reviewer for the approval.";
      setApprovalActionError(message);
      toast.error(message);
      return;
    }
    if (!approvalReviewerOptions.includes(reviewer)) {
      const message = "Approval assignee must be an existing DocReview360 user.";
      setApprovalActionError(message);
      toast.error(message);
      return;
    }
    try {
      setAddingApproval(true);
      setApprovalActionError(null);
      const created = await createApprovalForReviewer(reviewer);
      if (!created) {
        const message = "Approval already exists for this reviewer in the current phase.";
        setApprovalActionError(message);
        toast(message);
        return;
      }
      setApprovalReviewerInput("");
      toast.success("Approval added.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to add approval";
      setApprovalActionError(message);
      toast.error(message);
    } finally {
      setAddingApproval(false);
    }
  }, [approvalReviewerInput, approvalReviewerOptions, createApprovalForReviewer]);

  const handleAssignApproval = useCallback(
    async (approvalId: string, reviewer: string) => {
      try {
        const res = await authenticatedFetch(`/approvals/${approvalId}/assign`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reviewer }),
        });
        if (!res.ok) {
          let detail = "Failed to assign reviewer";
          try {
            const data = await res.json();
            if (typeof data?.detail === "string") detail = data.detail;
          } catch { /* ignore */ }
          toast.error(detail);
          return;
        }
        const updated = await res.json();
        setApprovals((prev) =>
          prev.map((a) =>
            a.id === approvalId ? { ...a, reviewer: updated.reviewer, email: updated.reviewer } : a,
          ),
        );
        toast.success(`Assigned ${reviewer} to role.`);
        refreshReviewerData();
      } catch {
        toast.error("Failed to assign reviewer.");
      }
    },
    [refreshReviewerData, setApprovals],
  );

  const handleUpdateReviewer = useCallback(async () => {
    if (!editingReviewer) return;
    const reviewer = editingValue.trim();
    if (!reviewer) { toast.error("Reviewer name required."); return; }
    try {
      await updateReviewer({ reviewer: editingReviewer, nextReviewer: reviewer });
      setEditingReviewer(null);
      setEditingValue("");
      refreshReviewerData();
    } catch (error) {
      console.warn("[useReviewerManagement]", error);
    }
  }, [editingReviewer, editingValue, updateReviewer, refreshReviewerData]);

  const handleRemoveReviewer = useCallback(
    async (reviewer: string) => {
      try {
        await removeReviewer(reviewer);
        refreshReviewerData();
      } catch (error) {
        console.warn("[useReviewerManagement]", error);
      }
    },
    [removeReviewer, refreshReviewerData],
  );

  return {
    reviewerInput, setReviewerInput,
    reviewerActionError, setReviewerActionError,
    addingReviewer,
    approvalReviewerInput, setApprovalReviewerInput,
    approvalActionError, setApprovalActionError,
    addingApproval,
    editingReviewer, setEditingReviewer,
    editingValue, setEditingValue,
    refreshReviewerData,
    createApprovalForReviewer,
    handleAddReviewer,
    handleAddApproval,
    handleAssignApproval,
    handleUpdateReviewer,
    handleRemoveReviewer,
  };
}
