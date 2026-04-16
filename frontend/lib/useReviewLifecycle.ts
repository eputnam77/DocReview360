import { useState } from "react";
import { toast } from "react-hot-toast";
import { authenticatedFetch } from "@/lib/api";
import { promptInBrowser } from "@/lib/browser";

export interface ReviewLifecycleState {
  assignmentReviewerInput: string;
  setAssignmentReviewerInput: React.Dispatch<React.SetStateAction<string>>;
  assignmentDueDate: string;
  setAssignmentDueDate: React.Dispatch<React.SetStateAction<string>>;
  addingAssignment: boolean;
  handleAddAssignment: () => Promise<void>;
  handleSendReminder: (assignmentId: string) => Promise<void>;
  handleSignInternal: (assignmentId: string) => Promise<void>;
  handleConcur: (assignmentId: string) => Promise<void>;
  handleNonConcur: (assignmentId: string) => Promise<void>;
  handleSubmitReview: (assignmentId: string) => Promise<void>;
  handleLifecycleTransition: (newStatus: string) => Promise<void>;
}

export function useReviewLifecycle({
  id,
  refetchAssignments,
  refetchMyAssignments,
  refetchSummary,
  refetchLifecycle,
}: {
  id: string | undefined;
  refetchAssignments: () => void;
  refetchMyAssignments: () => void;
  refetchSummary: () => void;
  refetchLifecycle: () => void;
}): ReviewLifecycleState {
  const [assignmentReviewerInput, setAssignmentReviewerInput] = useState("");
  const [assignmentDueDate, setAssignmentDueDate] = useState("");
  const [addingAssignment, setAddingAssignment] = useState(false);

  const handleAddAssignment = async () => {
    const reviewer = assignmentReviewerInput.trim();
    if (!reviewer) { toast.error("Enter a reviewer username."); return; }
    try {
      setAddingAssignment(true);
      const body: Record<string, unknown> = { reviewer };
      if (assignmentDueDate) body.due_date = assignmentDueDate;
      const res = await authenticatedFetch(`/projects/${id}/assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail ?? "Failed to add reviewer");
      }
      setAssignmentReviewerInput("");
      setAssignmentDueDate("");
      refetchAssignments();
      toast.success("Reviewer invited.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add reviewer");
    } finally {
      setAddingAssignment(false);
    }
  };

  const handleSendReminder = async (assignmentId: string) => {
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/remind`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error("Failed");
      toast.success("Reminder sent.");
    } catch {
      toast.error("Failed to send reminder.");
    }
  };

  const handleSignInternal = async (assignmentId: string) => {
    const note = promptInBrowser("Optional note for internal acknowledgement:");
    if (note === null) return;
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/sign-internal`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ note: note || null }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to sign");
        return;
      }
      toast.success("Internally acknowledged.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
    } catch {
      toast.error("Failed to sign.");
    }
  };

  const handleConcur = async (assignmentId: string) => {
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/concur`,
        { method: "POST" },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to concur");
        return;
      }
      toast.success("Concurred.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
    } catch {
      toast.error("Failed to concur.");
    }
  };

  const handleNonConcur = async (assignmentId: string) => {
    const reason = promptInBrowser("Add the reason for non-concurrence:");
    if (!reason?.trim()) return;
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/non-concur`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: reason.trim() }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to non-concur");
        return;
      }
      toast.success("Marked as non-concurred.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
    } catch {
      toast.error("Failed to non-concur.");
    }
  };

  const handleSubmitReview = async (assignmentId: string) => {
    try {
      const res = await authenticatedFetch(
        `/projects/${id}/assignments/${assignmentId}/submit`,
        { method: "POST" },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to submit review");
        return;
      }
      toast.success("Review submitted. The SME has been notified.");
      refetchAssignments();
      refetchMyAssignments();
      refetchSummary();
    } catch {
      toast.error("Failed to submit review.");
    }
  };

  const handleLifecycleTransition = async (newStatus: string) => {
    if (!confirm(`Transition project status to "${newStatus.replace(/_/g, " ")}"?`)) return;
    try {
      const res = await authenticatedFetch(`/projects/${id}/lifecycle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to transition status");
        return;
      }
      refetchLifecycle();
      toast.success(`Project status → ${newStatus.replace(/_/g, " ")}`);
    } catch {
      toast.error("Failed to transition project status.");
    }
  };

  return {
    assignmentReviewerInput, setAssignmentReviewerInput,
    assignmentDueDate, setAssignmentDueDate,
    addingAssignment,
    handleAddAssignment,
    handleSendReminder,
    handleSignInternal,
    handleConcur,
    handleNonConcur,
    handleSubmitReview,
    handleLifecycleTransition,
  };
}
