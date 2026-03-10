/**
 * React Query hooks for user session management.
 * Surfaces active sessions and allows revoking individual sessions.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import { API, authenticatedFetch } from "./api";

export interface UserSession {
  session_id: string;
  jti: string;
  created_at: string;
  last_active_at: string;
  expires_at: string;
  ip_address: string | null;
  user_agent: string | null;
  auth_method: string;
}

const SESSIONS_KEY = ["sessions"] as const;

/** Fetch all active sessions for the current user. */
export function useSessions() {
  return useQuery<UserSession[]>({
    queryKey: SESSIONS_KEY,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/sessions`);
      if (!res.ok) {
        if (res.status === 404) return [];
        throw new Error("Failed to fetch sessions");
      }
      return res.json();
    },
  });
}

/** Revoke a specific session. */
export function useRevokeSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: string) => {
      const res = await authenticatedFetch(`${API}/sessions/${sessionId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to revoke session");
    },
    onMutate: async (sessionId) => {
      await queryClient.cancelQueries({ queryKey: SESSIONS_KEY });
      const previous = queryClient.getQueryData(SESSIONS_KEY);
      queryClient.setQueryData(SESSIONS_KEY, (old: UserSession[] | undefined) =>
        old?.filter((s) => s.session_id !== sessionId) ?? [],
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      queryClient.setQueryData(SESSIONS_KEY, context?.previous);
      toast.error("Failed to revoke session");
    },
    onSuccess: () => {
      toast.success("Session revoked");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });
}
