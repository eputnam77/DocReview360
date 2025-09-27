import { create } from "zustand";
import { authenticatedFetch } from "@/lib/api";

interface UserState {
  isAdmin: boolean;
  isAuditor: boolean;
  username: string;
  theme: "system" | "light" | "dark";
  initialized: boolean;
  setAdmin: (value: boolean) => void;
  setAuditor: (value: boolean) => void;
  setUsername: (name: string) => void;
  setTheme: (value: "system" | "light" | "dark") => void;
  initialize: () => Promise<void>;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useUserStore = create<UserState>((set, get) => ({
  // Defaults are unauthenticated until initialize() fetches the session
  isAdmin: false,
  isAuditor: false,
  username: "",
  theme: "system",
  initialized: false,
  setAdmin: (value) => set({ isAdmin: value }),
  setAuditor: (value) => set({ isAuditor: value }),
  setUsername: (name) => set({ username: name }),
  setTheme: (value) => set({ theme: value }),
  async initialize() {
    if (get().initialized) {
      return;
    }

    try {
      const resp = await authenticatedFetch("/users/me");
      if (resp.status === 401) {
        set({
          isAdmin: false,
          isAuditor: false,
          username: "",
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
        set({
          username: data.username ?? "",
          isAdmin: Array.isArray(data.roles) && data.roles.includes("admin"),
          isAuditor: Array.isArray(data.roles) && data.roles.includes("auditor"),
          initialized: true,
        });
      }
      const prefsResp = await authenticatedFetch("/profile");
      if (prefsResp.ok) {
        const pdata = await prefsResp.json();
        const theme = ["system", "light", "dark"].includes(pdata.preferences?.theme)
          ? pdata.preferences.theme
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
    await get().initialize();
  },
  // Logout function to clear user data
  async logout() {
    try {
      await authenticatedFetch("/logout", { method: "POST" });
    } catch {
      // ignore logout errors
    }
    set({
      isAdmin: false,
      isAuditor: false,
      username: "",
      theme: "system",
      initialized: false,
    });
  },
}));
