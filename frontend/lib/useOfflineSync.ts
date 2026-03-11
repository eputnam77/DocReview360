/**
 * useOfflineSync — monitors online/offline state and syncs pending drafts
 * back to the server when connectivity is restored.
 *
 * Returns:
 *   isOnline      — whether the browser believes it has a network connection
 *   pendingCount  — number of drafts waiting to be synced
 *   syncNow       — imperatively trigger a sync attempt
 *   lastSyncAt    — timestamp of the last completed sync pass (or null)
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { authenticatedFetch } from "./api";
import { clearDraft, getPendingDrafts, loadOfflineDraft } from "./offlineStorage";

export interface OfflineSyncResult {
  isOnline: boolean;
  pendingCount: number;
  syncNow: () => void;
  lastSyncAt: Date | null;
}

export function useOfflineSync(): OfflineSyncResult {
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [lastSyncAt, setLastSyncAt] = useState<Date | null>(null);

  // Prevent concurrent sync runs.
  const syncInProgress = useRef(false);

  // Refresh the pending-count badge without running a full sync.
  const refreshCount = useCallback(async () => {
    const pending = await getPendingDrafts();
    setPendingCount(pending.length);
  }, []);

  const syncPendingDrafts = useCallback(async () => {
    if (syncInProgress.current) return;
    syncInProgress.current = true;
    try {
      const pending = await getPendingDrafts();
      if (pending.length === 0) return;

      for (const { docId } of pending) {
        const draft = await loadOfflineDraft(docId);
        if (!draft) continue;
        try {
          const res = await authenticatedFetch(`/documents/${docId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: draft.content }),
          });
          if (res.ok) {
            await clearDraft(docId);
          }
          // If the server returns a non-OK status we leave the draft pending
          // so it will be retried on the next sync.
        } catch {
          // Network error for this specific document — leave pending.
        }
      }

      // Refresh count after the sweep.
      const remaining = await getPendingDrafts();
      setPendingCount(remaining.length);
      setLastSyncAt(new Date());
    } finally {
      syncInProgress.current = false;
    }
  }, []);

  // Sync immediately when the browser transitions back online.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleOnline = () => {
      setIsOnline(true);
      syncPendingDrafts();
    };
    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Bootstrap the pending count on mount.
    refreshCount();

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [syncPendingDrafts, refreshCount]);

  const syncNow = useCallback(() => {
    if (isOnline) syncPendingDrafts();
  }, [isOnline, syncPendingDrafts]);

  return { isOnline, pendingCount, syncNow, lastSyncAt };
}
