import { create } from "zustand";
import { authenticatedFetch } from "@/lib/api";

interface UserState {
  isAdmin: boolean;
  isAuditor: boolean;
  username: string;
  theme: "system" | "light" | "dark";
  setAdmin: (value: boolean) => void;
  setAuditor: (value: boolean) => void;
  setUsername: (name: string) => void;
  setTheme: (value: "system" | "light" | "dark") => void;
  initialize: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useUserStore = create<UserState>((set) => ({
  // Defaults are unauthenticated until initialize() fetches the session
  isAdmin: false,
  isAuditor: false,
  username: "",
  theme: "system",
  setAdmin: (value) => set({ isAdmin: value }),
  setAuditor: (value) => set({ isAuditor: value }),
  setUsername: (name) => set({ username: name }),
  setTheme: (value) => set({ theme: value }),
  async initialize() {
    try {
      const resp = await authenticatedFetch("/users/me");
      if (resp.ok) {
        const data = await resp.json();
        set({
          username: data.username,
          isAdmin: Array.isArray(data.roles) && data.roles.includes("admin"),
          isAuditor: Array.isArray(data.roles) && data.roles.includes("auditor"),
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
    }
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
    });
  },
}));
