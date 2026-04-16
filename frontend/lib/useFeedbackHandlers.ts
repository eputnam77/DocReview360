import { useState } from "react";
import { toast } from "react-hot-toast";
import { authenticatedFetch } from "@/lib/api";

export interface FeedbackHandlersState {
  newFeedbackText: string;
  setNewFeedbackText: React.Dispatch<React.SetStateAction<string>>;
  newFeedbackType: string;
  setNewFeedbackType: React.Dispatch<React.SetStateAction<string>>;
  replyText: Record<string, string>;
  setReplyText: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  expandedFeedback: Set<string>;
  setExpandedFeedback: React.Dispatch<React.SetStateAction<Set<string>>>;
  feedbackTypeFilter: string;
  setFeedbackTypeFilter: React.Dispatch<React.SetStateAction<string>>;
  feedbackStatusFilter: string;
  setFeedbackStatusFilter: React.Dispatch<React.SetStateAction<string>>;
  feedbackShowMyOnly: boolean;
  setFeedbackShowMyOnly: React.Dispatch<React.SetStateAction<boolean>>;
  handlePostFeedback: () => Promise<void>;
  handleDisposition: (itemId: string, status: string, reason?: string) => Promise<void>;
  handleReply: (parentId: string) => Promise<void>;
}

export function useFeedbackHandlers({
  id,
  refetchFeedback,
  refetchProgress,
}: {
  id: string | undefined;
  refetchFeedback: () => void;
  refetchProgress: () => void;
}): FeedbackHandlersState {
  const [newFeedbackText, setNewFeedbackText] = useState("");
  const [newFeedbackType, setNewFeedbackType] = useState("comment");
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [expandedFeedback, setExpandedFeedback] = useState<Set<string>>(new Set());
  const [feedbackTypeFilter, setFeedbackTypeFilter] = useState("all");
  const [feedbackStatusFilter, setFeedbackStatusFilter] = useState("all");
  const [feedbackShowMyOnly, setFeedbackShowMyOnly] = useState(false);

  const handlePostFeedback = async () => {
    if (!newFeedbackText.trim()) return;
    try {
      const res = await authenticatedFetch(`/projects/${id}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: newFeedbackText, feedback_type: newFeedbackType }),
      });
      if (!res.ok) throw new Error("Failed");
      setNewFeedbackText("");
      refetchFeedback();
      refetchProgress();
      toast.success("Feedback submitted.");
    } catch {
      toast.error("Failed to submit feedback.");
    }
  };

  const handleDisposition = async (itemId: string, status: string, reason?: string) => {
    try {
      const body: Record<string, unknown> = { status };
      if (reason) body.reason = reason;
      const res = await authenticatedFetch(`/projects/${id}/feedback/${itemId}/disposition`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed");
      refetchFeedback();
      refetchProgress();
      toast.success(`Marked as ${status}.`);
    } catch {
      toast.error("Failed to update status.");
    }
  };

  const handleReply = async (parentId: string) => {
    const text = replyText[parentId]?.trim();
    if (!text) return;
    try {
      const res = await authenticatedFetch(`/projects/${id}/feedback/${parentId}/reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error("Failed");
      setReplyText((prev) => ({ ...prev, [parentId]: "" }));
      refetchFeedback();
      toast.success("Reply posted.");
    } catch {
      toast.error("Failed to post reply.");
    }
  };

  return {
    newFeedbackText, setNewFeedbackText,
    newFeedbackType, setNewFeedbackType,
    replyText, setReplyText,
    expandedFeedback, setExpandedFeedback,
    feedbackTypeFilter, setFeedbackTypeFilter,
    feedbackStatusFilter, setFeedbackStatusFilter,
    feedbackShowMyOnly, setFeedbackShowMyOnly,
    handlePostFeedback,
    handleDisposition,
    handleReply,
  };
}
