import { create } from "zustand";

interface UserState {
  isAdmin: boolean;
  username: string;
  setAdmin: (value: boolean) => void;
  setUsername: (name: string) => void;
}

export const useUserStore = create<UserState>((set) => ({
  isAdmin: true,
  username: "demo",
  setAdmin: (value) => set(() => ({ isAdmin: value })),
  setUsername: (name) => set(() => ({ username: name })),
}));
