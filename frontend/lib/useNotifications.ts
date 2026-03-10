/**
 * React Query hooks for notification fetching and management.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import { API, authenticatedFetch } from "./api";

export interface Notification {
  id: string;
  type: string;
  message: string;
  read: boolean;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface NotificationSettings {
  email_enabled: boolean;
  slack_enabled: boolean;
  slack_webhook_url?: string;
  teams_enabled: boolean;
  teams_webhook_url?: string;
  notify_on_approval_request: boolean;
  notify_on_approval_complete: boolean;
  notify_on_rejection: boolean;
  notify_on_comment: boolean;
}

const NOTIFICATIONS_KEY = ["notifications"] as const;
const NOTIFICATION_SETTINGS_KEY = ["notification-settings"] as const;

/** Fetch unread notifications for the current user. */
export function useNotifications() {
  return useQuery<Notification[]>({
    queryKey: NOTIFICATIONS_KEY,
    // Poll every 60 seconds to catch new notifications
    refetchInterval: 60_000,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/notifications`);
      if (!res.ok) {
        if (res.status === 404) return []; // endpoint may not be enabled
        throw new Error("Failed to fetch notifications");
      }
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    },
  });
}

/** Return the count of unread notifications. */
export function useUnreadNotificationCount(): number {
  const { data } = useNotifications();
  return data?.filter((n) => !n.read).length ?? 0;
}

/** Mark a notification as read. */
export function useMarkNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notificationId: string) => {
      const res = await authenticatedFetch(`${API}/notifications/${notificationId}/read`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to mark notification as read");
    },
    onMutate: async (notificationId) => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_KEY });
      const previous = queryClient.getQueryData(NOTIFICATIONS_KEY);
      queryClient.setQueryData(NOTIFICATIONS_KEY, (old: Notification[] | undefined) =>
        old?.map((n) => (n.id === notificationId ? { ...n, read: true } : n)) ?? [],
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      queryClient.setQueryData(NOTIFICATIONS_KEY, context?.previous);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
    },
  });
}

/** Mark all notifications as read. */
export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await authenticatedFetch(`${API}/notifications/read-all`, { method: "POST" });
      if (!res.ok && res.status !== 404) throw new Error("Failed to mark all as read");
    },
    onSuccess: () => {
      queryClient.setQueryData(NOTIFICATIONS_KEY, (old: Notification[] | undefined) =>
        old?.map((n) => ({ ...n, read: true })) ?? [],
      );
    },
  });
}

/** Fetch notification settings. */
export function useNotificationSettings() {
  return useQuery<NotificationSettings>({
    queryKey: NOTIFICATION_SETTINGS_KEY,
    queryFn: async () => {
      const res = await authenticatedFetch(`${API}/notifications/settings`);
      if (!res.ok) throw new Error("Failed to fetch notification settings");
      return res.json();
    },
  });
}

/** Update notification settings. */
export function useUpdateNotificationSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (settings: Partial<NotificationSettings>) => {
      const res = await authenticatedFetch(`${API}/notifications/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!res.ok) throw new Error("Failed to update notification settings");
      return res.json() as Promise<NotificationSettings>;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(NOTIFICATION_SETTINGS_KEY, updated);
      toast.success("Notification settings saved");
    },
    onError: () => {
      toast.error("Failed to save notification settings");
    },
  });
}
