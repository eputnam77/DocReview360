import { useQuery } from "@tanstack/react-query";

import { authenticatedFetch } from "@/lib/api";
import type { VersionEntry } from "@/components/project/_types";

interface ReviewAssignment {
  id: string;
  reviewer: string;
  status: string;
  requested_at: string;
  due_date?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  signed_at?: string | null;
  replaced_by?: string | null;
  replacement_reason?: string | null;
}

interface FeedbackItem {
  id: string;
  reviewer: string;
  feedback_type: string;
  text: string;
  phase?: string | null;
  status: string;
  created_at: string;
  disposition_by?: string | null;
  disposition_at?: string | null;
  disposition_reason?: string | null;
  parent_id?: string | null;
  tags: string[];
  question_satisfied: boolean;
  assignment_id?: string | null;
  source?: string | null;
  range_anchor?: string | null;
}

interface FeedbackProgress {
  total: number;
  open: number;
  accepted: number;
  rejected: number;
  resolved: number;
  addressed: number;
  by_type: Record<string, number>;
}

interface NotifLogEntry {
  id: string;
  event: string;
  message: string;
  reviewer?: string | null;
  sent_at: string;
  channel: string;
}

interface ReviewSummary {
  total_active: number;
  invited: number;
  reviewing: number;
  feedback_submitted: number;
  concurred: number;
  non_concurred: number;
  signed: number;
  declined: number;
  all_complete: boolean;
  all_signed: boolean;
  has_non_concurrence: boolean;
  lifecycle_step: string;
  feedback_total: number;
  feedback_open: number;
  feedback_addressed: number;
}

interface LifecycleRecord {
  project_id: string;
  status: string;
  updated_at: string;
  set_by?: string | null;
  published_ref?: string | null;
  published_at?: string | null;
  published_venue?: string | null;
}

interface DocumentScore {
  document_id: string;
  quality_score: number;
  plain_language_grade: string;
  flesch_reading_ease: number;
  quality_flags: Record<string, number>;
  high_risk_terms: string[];
  doc_type_avg_score: number | null;
}

interface UserDirectoryEntry {
  username?: string | null;
}

export function useProjectReviewCycleData(id: string | undefined) {
  const userOptionsQuery = useQuery<UserDirectoryEntry[]>({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await authenticatedFetch("/users");
      if (!res.ok) return [];
      return res.json();
    },
  });

  const assignmentsQuery = useQuery<ReviewAssignment[]>({
    queryKey: ["assignments", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/assignments`);
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : (data.items ?? []);
    },
    enabled: !!id,
    staleTime: 30_000,
  });

  const reviewSummaryQuery = useQuery<ReviewSummary>({
    queryKey: ["review-summary", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await authenticatedFetch(`/projects/${id}/review-summary`);
      return res.ok ? res.json() : null;
    },
    enabled: !!id,
    staleTime: 15_000,
  });

  const myAssignmentsQuery = useQuery<ReviewAssignment[]>({
    queryKey: ["my-assignments", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/assignments/me`);
      return res.ok ? res.json() : [];
    },
    enabled: !!id,
    staleTime: 30_000,
  });

  const lifecycleQuery = useQuery<LifecycleRecord>({
    queryKey: ["lifecycle", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await authenticatedFetch(`/projects/${id}/lifecycle`);
      return res.ok ? res.json() : { project_id: id, status: "draft", updated_at: "" };
    },
    enabled: !!id,
    staleTime: 30_000,
  });

  return {
    userOptionsQuery,
    assignmentsQuery,
    reviewSummaryQuery,
    myAssignmentsQuery,
    lifecycleQuery,
  };
}

export function useProjectFeedbackData(id: string | undefined) {
  const feedbackItemsQuery = useQuery<FeedbackItem[]>({
    queryKey: ["feedback", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/feedback`);
      if (!res.ok) return [];
      const data = await res.json();
      if (Array.isArray(data)) return data as FeedbackItem[];
      if (data && Array.isArray(data.items)) return data.items as FeedbackItem[];
      return [];
    },
    enabled: !!id,
    staleTime: 15_000,
  });

  const feedbackProgressQuery = useQuery<FeedbackProgress>({
    queryKey: ["feedback-progress", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await authenticatedFetch(`/projects/${id}/feedback/progress`);
      return res.ok ? res.json() : null;
    },
    enabled: !!id,
    staleTime: 15_000,
  });

  const notifLogQuery = useQuery<NotifLogEntry[]>({
    queryKey: ["notif-log", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await authenticatedFetch(`/projects/${id}/notification-log`);
      return res.ok ? res.json() : [];
    },
    enabled: !!id,
    staleTime: 60_000,
  });

  return {
    feedbackItemsQuery,
    feedbackProgressQuery,
    notifLogQuery,
  };
}

export function useProjectDocumentScores(id: string | undefined) {
  return useQuery<DocumentScore[]>({
    queryKey: ["project-doc-scores", id],
    queryFn: async () => {
      const res = await authenticatedFetch(`/projects/${id}/documents/scores`);
      if (!res.ok) return [];
      return res.json();
    },
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useProjectVersionHistory(documentId: string | undefined) {
  return useQuery<VersionEntry[]>({
    queryKey: ["document-versions", documentId],
    queryFn: async () => {
      if (!documentId) return [];
      const res = await authenticatedFetch(`/documents/${documentId}/versions`);
      return res.ok ? res.json() : [];
    },
    enabled: !!documentId,
    staleTime: 60_000,
  });
}

export function useProjectFSVStatus() {
  return useQuery<boolean>({
    queryKey: ["fsv-enabled"],
    queryFn: async () => {
      const res = await authenticatedFetch("/plugin-marketplace/builtin-status");
      if (!res.ok) return true;
      const status: Record<string, boolean> = await res.json();
      return status["fedstylevalidator"] !== false;
    },
    staleTime: 60_000,
  });
}
