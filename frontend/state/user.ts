import { create } from "zustand";

interface UserState {
  isAdmin: boolean;
  username: string;
  setAdmin: (value: boolean) => void;
  setUsername: (name: string) => void;
  initialize: () => Promise<void>;
}

export const useUserStore = create<UserState>((set) => ({
  isAdmin: true,
  username: "demo",
  setAdmin: (value) => set({ isAdmin: value }),
  setUsername: (name) => set({ username: name }),
  async initialize() {
    try {
      const resp = await fetch("/api/users/me");
      if (resp.ok) {
        const data = await resp.json();
        set({ username: data.username, isAdmin: data.is_admin });
      }
    } catch {
      // ignore errors and keep defaults
    }
  },
}));
