import { create } from "zustand";
import { authenticatedFetch, clearStoredAccessToken } from "@/lib/api";

const SESSION_COOKIE_NAMES = ["access_token", "session", "sessionid"];

const hasSessionCookie = () => {
  if (typeof document === "undefined" || !document.cookie) {
    return false;
  }

  const cookies = document.cookie.split(";").map((cookie) => cookie.trim());
  return cookies.some((cookie) =>
    SESSION_COOKIE_NAMES.some((name) => cookie.startsWith(`${name}=`)),
  );
};

interface UserState {
  isAdmin: boolean;
  isAuditor: boolean;
  username: string;
  inactivityTimeoutMinutes: number;
  theme: "system" | "light" | "dark";
  initialized: boolean;
  setAdmin: (value: boolean) => void;
  setAuditor: (value: boolean) => void;
  setUsername: (name: string) => void;
  setTheme: (value: "system" | "light" | "dark") => void;
  initialize: (force?: boolean) => Promise<void>;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useUserStore = create<UserState>((set, get) => ({
  // Defaults are unauthenticated until initialize() fetches the session
  isAdmin: false,
  isAuditor: false,
  username: "",
  inactivityTimeoutMinutes: 30,
  theme: "system",
  initialized: false,
  setAdmin: (value) => set({ isAdmin: value }),
  setAuditor: (value) => set({ isAuditor: value }),
  setUsername: (name) => set({ username: name }),
  setTheme: (value) => set({ theme: value }),
  async initialize(force = false) {
    if (get().initialized && !force) {
      return;
    }

    if (!force && !hasSessionCookie()) {
      set({
        isAdmin: false,
        isAuditor: false,
        username: "",
        inactivityTimeoutMinutes: 30,
        theme: "system",
        initialized: true,
      });
      return;
    }

    try {
      const resp = await authenticatedFetch("/users/me");
      if (resp.status === 401) {
        set({
          isAdmin: false,
          isAuditor: false,
          username: "",
          inactivityTimeoutMinutes: 30,
          theme: "system",
          initialized: true,
        });
        return;
      }

      if (!resp.ok) {
        set({ initialized: true });
        return;
      }

      if (resp.ok) {
        const data = await resp.json();
        const timeoutMinutesRaw = data.inactivity_timeout_minutes;
        const timeoutMinutes =
          typeof timeoutMinutesRaw === "number" &&
          Number.isFinite(timeoutMinutesRaw) &&
          timeoutMinutesRaw > 0
            ? timeoutMinutesRaw
            : 30;
        set({
          username: data.username ?? "",
          isAdmin: Array.isArray(data.roles) && data.roles.includes("admin"),
          isAuditor: Array.isArray(data.roles) && data.roles.includes("auditor"),
          inactivityTimeoutMinutes: timeoutMinutes,
          initialized: true,
        });
      }
      const prefsResp = await authenticatedFetch("/profile");
      if (prefsResp.ok) {
        const pdata = await prefsResp.json();
        const prefTheme = pdata?.preferences?.theme;
        const rootTheme = pdata?.theme;
        const themeCandidate = typeof prefTheme === "string" ? prefTheme : rootTheme;
        const theme = ["system", "light", "dark"].includes(themeCandidate)
          ? (themeCandidate as "system" | "light" | "dark")
          : "system";
        set({ theme });
      }
    } catch {
      // ignore errors and keep defaults
      set({ initialized: false });
    }
  },
  async refresh() {
    set({ initialized: false });
    await get().initialize(true);
  },
  // Logout function to clear user data
  async logout() {
    try {
      await authenticatedFetch("/logout", { method: "POST" });
    } catch {
      // ignore logout errors
    }
    clearStoredAccessToken();
    set({
      isAdmin: false,
      isAuditor: false,
      username: "",
      inactivityTimeoutMinutes: 30,
      theme: "system",
      initialized: false,
    });
  },
}));

