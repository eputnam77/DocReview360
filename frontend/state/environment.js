import { create } from "zustand";
import { authenticatedFetch } from "@/lib/api";
export const useEnvStore = create((set) => ({
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
        }
        catch (error) {
            console.error("Unable to load environments", error);
        }
    },
    switchEnv: async (name) => {
        try {
            const response = await authenticatedFetch(`/environments/${name}`, { method: "POST" });
            if (!response.ok) {
                console.warn("Failed to switch environment", response.status, response.statusText);
                return;
            }
            set((state) => ({ current: state.envs[name] }));
        }
        catch (error) {
            console.error("Unable to switch environment", error);
        }
    },
}));
