import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API } from "./api";
import { toast } from "react-hot-toast";

export interface Approval {
  id: string;
  reviewer: string;
  email: string;
  state: "pending" | "approved" | "overdue" | "rejected";
  dueAt: string;
  signedAt?: string;
  comments?: string;
  documensoSigId?: string;
  description?: string;
  phaseId?: string;
  required?: boolean;
  signature_provider?: string;
  signature_id?: string;
  certificate_url?: string;
}

interface Options {
  workflow?: string;
  phase?: string;
  id?: string;
}

const mapApproval = (approval: any): Approval => ({
  id: approval.id,
  reviewer: approval.reviewer,
  email: approval.reviewer,
  state: approval.state,
  dueAt: approval.due_at || new Date().toISOString().split("T")[0],
  signedAt: approval.signed_at,
  comments: approval.comments || "",
  documensoSigId: approval.signature || approval.signature_id,
  description: approval.description,
  phaseId: approval.phase_id,
  required: approval.required,
  signature_provider: approval.signature_provider,
  signature_id: approval.signature_id,
  certificate_url: approval.certificate_url,
});

export function useApprovals({ workflow, phase, id }: Options) {
  const queryClient = useQueryClient();
  const queryKey = id ? ["approval", id] : ["approvals", workflow, phase];

  const query = useQuery({
    queryKey,
    enabled: id ? !!id : !!workflow,
    queryFn: async () => {
      if (id) {
        const res = await fetch(`${API}/approvals/${id}`);
        if (!res.ok) throw new Error("Failed to fetch approval");
        const data = await res.json();
        return mapApproval(data);
      }
      const phaseParam = phase ? `&phase=${encodeURIComponent(phase)}` : "";
      const res = await fetch(`${API}/approvals?workflow=${workflow}${phaseParam}`);
      if (!res.ok) throw new Error("Failed to fetch approvals");
      const data = await res.json();
      return Array.isArray(data) ? data.map(mapApproval) : [];
    },
  });

  const approveMutation = useMutation({
    mutationFn: async (aid: string) => {
      const res = await fetch(`${API}/approvals/${aid}/sign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error("Failed to start signing");
      return res.json();
    },
    onMutate: async (aid: string) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData(queryKey);
      queryClient.setQueryData(queryKey, (old: any) => {
        const update = (a: Approval) =>
          a.id === aid ? { ...a, state: "approved", signedAt: new Date().toISOString() } : a;
        if (Array.isArray(old)) return old.map(update);
        return update(old);
      });
      return { previous };
    },
    onError: (_err, _aid, context) => {
      queryClient.setQueryData(queryKey, context?.previous);
      toast.error("Failed to approve");
    },
    onSuccess: (data, aid) => {
      const sigId = data?.id ?? data?.signature?.id;
      if (sigId) {
        queryClient.setQueryData(queryKey, (old: any) => {
          const update = (a: Approval) =>
            a.id === aid ? { ...a, documensoSigId: sigId } : a;
          if (Array.isArray(old)) return old.map(update);
          return update(old);
        });
      }
      toast.success("Approval signed");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const resetMutation = useMutation({
    mutationFn: async (aid: string) => {
      const res = await fetch(`${API}/approvals/${aid}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: "pending", signature: null }),
      });
      if (!res.ok) throw new Error("Failed to reset approval");
      return res.json();
    },
    onMutate: async (aid: string) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData(queryKey);
      queryClient.setQueryData(queryKey, (old: any) => {
        const update = (a: Approval) =>
          a.id === aid
            ? { ...a, state: "pending", signedAt: undefined, documensoSigId: undefined }
            : a;
        if (Array.isArray(old)) return old.map(update);
        return update(old);
      });
      return { previous };
    },
    onError: (_err, _aid, context) => {
      queryClient.setQueryData(queryKey, context?.previous);
      toast.error("Failed to reset approval");
    },
    onSuccess: () => {
      toast.success("Approval reset");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const remindMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      const res = await fetch(`${API}/approvals/remind`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      });
      if (!res.ok) throw new Error("Failed to send reminder");
      return res.json();
    },
    onError: () => {
      toast.error("Failed to send reminder");
    },
    onSuccess: () => {
      toast.success("Reminder sent");
    },
  });

  return {
    approvals: Array.isArray(query.data) ? (query.data as Approval[]) : undefined,
    approval: !Array.isArray(query.data) ? (query.data as Approval) : undefined,
    isLoading: query.isLoading,
    error: query.error,
    approve: approveMutation.mutateAsync,
    reset: resetMutation.mutateAsync,
    remind: (ids?: string[]) => remindMutation.mutateAsync(ids ?? []),
  };
}

