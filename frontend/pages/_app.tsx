import type { AppProps } from "next/app";
import { useRouter } from "next/router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useEffect } from "react";

import AppFooter from "@/components/AppFooter";
import Sidebar from "../components/workflow/Sidebar";
import ThemeProvider from "../components/ThemeProvider";
import { useUserStore } from "../state/user";
import "../styles/globals.css";
import "../styles/tiptap.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 30 seconds — avoids refetching on every focus
      staleTime: 30_000,
      // Keep unused cache entries for 5 minutes before garbage-collecting
      gcTime: 5 * 60_000,
      // Retry failed queries at most twice with exponential backoff
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30_000),
      // Refetch when the browser tab regains focus (catches stale-while-away)
      refetchOnWindowFocus: true,
    },
    mutations: {
      // Surface mutation errors — callers handle toast notifications
      throwOnError: false,
    },
  },
});

export default function App({ Component, pageProps }: AppProps) {
  const init = useUserStore((s) => s.initialize);
  const initialized = useUserStore((s) => s.initialized);
  const username = useUserStore((s) => s.username);
  const inactivityTimeoutMinutes = useUserStore((s) => s.inactivityTimeoutMinutes);
  const logout = useUserStore((s) => s.logout);
  const router = useRouter();

  useEffect(() => {
    void init();
  }, [init]);

  useEffect(() => {
    if (!initialized || !username) {
      return;
    }

    const timeoutMs = Math.max(60_000, inactivityTimeoutMinutes * 60_000);
    let timerId: ReturnType<typeof setTimeout> | null = null;
    let loggingOut = false;

    const scheduleLogout = () => {
      if (timerId) {
        clearTimeout(timerId);
      }
      timerId = setTimeout(() => {
        if (loggingOut) {
          return;
        }
        loggingOut = true;
        void (async () => {
          await logout();
          await router.replace("/login");
        })();
      }, timeoutMs);
    };

    const markActive = () => {
      scheduleLogout();
    };

    const activityEvents: (keyof WindowEventMap)[] = [
      "pointerdown",
      "keydown",
      "wheel",
      "touchstart",
      "input",
    ];

    for (const eventName of activityEvents) {
      window.addEventListener(eventName, markActive);
    }

    const onRouteChangeComplete = () => {
      markActive();
    };
    router.events.on("routeChangeComplete", onRouteChangeComplete);

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        markActive();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    scheduleLogout();

    return () => {
      if (timerId) {
        clearTimeout(timerId);
      }
      for (const eventName of activityEvents) {
        window.removeEventListener(eventName, markActive);
      }
      router.events.off("routeChangeComplete", onRouteChangeComplete);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [
    inactivityTimeoutMinutes,
    initialized,
    logout,
    router,
    username,
  ]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <div className="flex min-h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
          <Sidebar />
          <main className="flex flex-1 flex-col overflow-y-auto">
            <Toaster position="top-right" />
            <div className="flex-1">
              <Component {...pageProps} />
            </div>
            <AppFooter />
          </main>
        </div>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
