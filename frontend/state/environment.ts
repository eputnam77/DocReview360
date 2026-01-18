import { create } from "zustand";
import { authenticatedFetch } from "@/lib/api";

export interface Environment {
  name: string;
  url: string;
  color: string;
}

interface EnvState {
  current?: Environment;
  envs: Record<string, Environment>;
  load: () => Promise<void>;
  switchEnv: (name: string) => Promise<void>;
}

export const useEnvStore = create<EnvState>((set) => ({
  current: undefined,
  envs: {},
  load: async () => {
    try {
      const response = await authenticatedFetch("/environments");
      if (!response.ok) {
        console.warn("Failed to load environments", response.status, response.statusText);
        return;
      }

      const data = await response.json();
      set({ current: data.current ?? undefined, envs: data.envs });
    } catch (error) {
      console.error("Unable to load environments", error);
    }
  },
  switchEnv: async (name: string) => {
    try {
      const response = await authenticatedFetch(`/environments/${name}`, { method: "POST" });
      if (!response.ok) {
        console.warn("Failed to switch environment", response.status, response.statusText);
        return;
      }

      set((state) => ({ current: state.envs[name] }));
    } catch (error) {
      console.error("Unable to switch environment", error);
    }
  },
}));
