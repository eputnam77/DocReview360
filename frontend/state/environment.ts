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
    const r = await authenticatedFetch("/environments");
    const data = await r.json();
    set({ current: data.current ?? undefined, envs: data.envs });
  },
  switchEnv: async (name: string) => {
    await authenticatedFetch(`/environments/${name}`, { method: "POST" });
    set((s) => ({ current: s.envs[name] }));
  },
}));
