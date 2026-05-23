import { useCallback } from "react";
import { useRouter } from "next/router";
import { toast } from "react-hot-toast";
import { authenticatedFetch } from "@/lib/api";
import { assignBrowserLocation, removeLocalStorage, resolveBrowserUrl } from "@/lib/browser";
import type { Approval } from "@/components/project/_types";
import type { AuditEntry } from "@/components/AuditTimeline";

export interface ApprovalSigningState {
  buildApprovalSigningRoute: (approvalId: string, signatureId: string) => string;
  routeToApprovalSignature: (
    approvalId: string,
    signatureId: string | undefined,
    signatureUrl: string | undefined,
  ) => boolean;
  signApproval: (aid: string) => Promise<void>;
  rejectApproval: (aid: string) => Promise<void>;
  signApprovalByInitials: (aid: string, initials: string) => Promise<void>;
  resetApprovalLocal: (aid: string) => Promise<void>;
  removeApproval: (aid: string) => Promise<void>;
  sendApprovalReminder: (ids?: string[]) => void;
  viewApprovalHistory: (aid: string) => void;
}

export function useApprovalSigning({
  id,
  username,
  approvals,
  approvalsForPhase,
  setApprovals,
  setHistoryEvents,
  setShowHistory,
  reset,
  remind,
}: {
  id: string | undefined;
  username: string | undefined | null;
  approvals: Approval[];
  approvalsForPhase: Approval[];
  setApprovals: React.Dispatch<React.SetStateAction<Approval[]>>;
  setHistoryEvents: React.Dispatch<React.SetStateAction<AuditEntry[]>>;
  setShowHistory: React.Dispatch<React.SetStateAction<boolean>>;
  reset: (aid: string) => Promise<void>;
  remind: (ids: string[]) => void;
}): ApprovalSigningState {
  const router = useRouter();

  const readAuditTimestamp = useCallback(
    (entry: { timestamp?: unknown; verified_at?: unknown }) =>
      typeof entry.timestamp === "string" && entry.timestamp.trim()
        ? entry.timestamp
        : typeof entry.verified_at === "string" && entry.verified_at.trim()
          ? entry.verified_at
          : null,
    [],
  );

  const buildApprovalSigningRoute = useCallback(
    (approvalId: string, signatureId: string) =>
      `/documenso/${encodeURIComponent(signatureId)}?return=${encodeURIComponent(
        `/projects/${id}#approvals`,
      )}&approval=${encodeURIComponent(approvalId)}`,
    [id],
  );

  const routeToApprovalSignature = useCallback(
    (approvalId: string, signatureId: string | undefined, signatureUrl: string | undefined): boolean => {
      if (signatureId) {
        const localSigningRoute = buildApprovalSigningRoute(approvalId, signatureId);
        if (!signatureUrl) {
          router.push(localSigningRoute);
          return true;
        }
        const parsed = resolveBrowserUrl(signatureUrl);
        const currentOrigin = resolveBrowserUrl("/")?.origin;
        if (parsed && currentOrigin && parsed.origin !== currentOrigin) {
          return !!assignBrowserLocation(parsed.href);
        }
        if (parsed) {
          if (parsed.pathname.startsWith("/documenso/")) {
            router.push(parsed.pathname + parsed.search + parsed.hash);
            return true;
          }
          router.push(localSigningRoute);
          return true;
        }
        router.push(localSigningRoute);
        return true;
      }
      if (!signatureUrl) return false;
      const parsed = resolveBrowserUrl(signatureUrl);
      const currentOrigin = resolveBrowserUrl("/")?.origin;
      if (!parsed) return false;
      if (currentOrigin && parsed.origin !== currentOrigin) {
        return !!assignBrowserLocation(parsed.href);
      }
      router.push(parsed.pathname + parsed.search + parsed.hash);
      return true;
    },
    [buildApprovalSigningRoute, router],
  );

  const signApproval = useCallback(async (aid: string) => {
    const existing = approvals.find((a) => a.id === aid);
    if (existing?.state === "approved") { toast.error("Approval already completed."); return; }
    if (existing?.reviewer !== username) { toast.error("You are not assigned to this approval."); return; }
    try {
      const res = await authenticatedFetch(`/approvals/${aid}/sign`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const signatureUrl: string | undefined = err?.url;
        const signatureId: string | undefined = err?.id ?? err?.signature ?? err?.signature_id;
        if (routeToApprovalSignature(aid, signatureId, signatureUrl)) return;
        toast.error(err?.detail ?? "Failed to submit approval");
        return;
      }
      const updated = await res.json();
      const signatureUrl: string | undefined = updated?.url;
      const signatureId: string | undefined = updated?.id ?? updated?.signature ?? updated?.signature_id;
      if (routeToApprovalSignature(aid, signatureId, signatureUrl)) return;
      if (updated?.state === "approved") {
        setApprovals((prev) => prev.map((a) => (a.id === aid ? { ...a, ...updated } : a)));
        toast.success("Approval recorded successfully.");
        return;
      }
      toast.error("Approval flow could not be started.");
    } catch {
      toast.error("Failed to submit approval. Please try again.");
    }
  }, [approvals, username, routeToApprovalSignature, setApprovals]);

  const rejectApproval = useCallback(async (aid: string) => {
    const existing = approvals.find((a) => a.id === aid);
    if (existing?.state === "rejected") { toast.error("Approval already marked as non-concurred."); return; }
    if (existing?.reviewer !== username) { toast.error("You are not assigned to this approval."); return; }
    if (!confirm("Mark this approval as non-concurred?")) return;
    try {
      const res = await authenticatedFetch(`/approvals/${aid}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: "rejected" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to mark approval as non-concurred");
        return;
      }
      const updated = await res.json();
      setApprovals((prev) => prev.map((a) => (a.id === aid ? { ...a, ...updated } : a)));
      toast.success("Approval marked as non-concurred.");
    } catch {
      toast.error("Failed to mark approval as non-concurred.");
    }
  }, [approvals, username, setApprovals]);

  const signApprovalByInitials = useCallback(async (aid: string, initials: string) => {
    const existing = approvals.find((a) => a.id === aid);
    if (existing?.state === "approved") { toast.error("Approval already completed."); return; }
    if (existing?.reviewer !== username) { toast.error("You are not assigned to this approval."); return; }
    try {
      const res = await authenticatedFetch(`/approvals/${aid}/sign-initials`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initials }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? "Failed to sign with initials");
        return;
      }
      const updated = await res.json();
      setApprovals((prev) => prev.map((a) => (a.id === aid ? { ...a, ...updated } : a)));
      toast.success("Approved with initials");
    } catch {
      toast.error("Failed to sign with initials");
    }
  }, [approvals, username, setApprovals]);

  const resetApprovalLocal = useCallback(async (aid: string) => {
    removeLocalStorage(`approval-${aid}`);
    try {
      await reset(aid);
    } catch { /* handled in hook */ }
  }, [reset]);

  const removeApproval = useCallback(async (aid: string) => {
    try {
      const response = await authenticatedFetch(`/approvals/${aid}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Failed to remove approval");
      setApprovals((prev) => prev.filter((x) => x.id !== aid));
      toast.success("Approval removed");
    } catch (error) {
      console.error("Error removing approval:", error);
      toast.error("Failed to remove approval");
    }
  }, [setApprovals]);

  const sendApprovalReminder = useCallback((ids?: string[]) => {
    const targets = approvalsForPhase.filter(
      (a) => (ids ? ids.includes(a.id) : true) && (a.state === "pending" || a.state === "overdue"),
    );
    remind(targets.map((a) => a.id));
  }, [approvalsForPhase, remind]);

  const viewApprovalHistory = useCallback((aid: string) => {
    authenticatedFetch(`/approvals/${aid}/history`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setHistoryEvents(
          data.flatMap((d, index) => {
            const timestamp = readAuditTimestamp(d);
            if (!timestamp) return [];
            return [{
              id:
                (typeof d?.id === "string" && d.id.trim()
                  ? d.id
                  : `${aid}-history-${index}`),
              timestamp,
              message:
                (typeof d?.event === "string" && d.event.trim()
                  ? d.event
                  : typeof d?.action === "string" && d.action.trim()
                    ? d.action
                    : typeof d?.message === "string" && d.message.trim()
                      ? d.message
                      : "approval_updated"),
              type: "approval" as const,
            }];
          }),
        ),
      )
      .catch(() => setHistoryEvents([]))
      .finally(() => setShowHistory(true));
  }, [readAuditTimestamp, setHistoryEvents, setShowHistory]);

  return {
    buildApprovalSigningRoute,
    routeToApprovalSignature,
    signApproval,
    rejectApproval,
    signApprovalByInitials,
    resetApprovalLocal,
    removeApproval,
    sendApprovalReminder,
    viewApprovalHistory,
  };
}
