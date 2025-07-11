import { create } from "zustand";

interface UserState {
  isAdmin: boolean;
  setAdmin: (value: boolean) => void;
}

export const useUserStore = create<UserState>((set) => ({
  isAdmin: true,
  setAdmin: (value) => set(() => ({ isAdmin: value })),
}));
