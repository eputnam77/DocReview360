import type { AppProps } from "next/app";
import { useRouter } from "next/router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import "../styles/globals.css";
import "../styles/tiptap.css";
import Sidebar from "../components/workflow/Sidebar";
import { useEffect } from "react";
import { useUserStore } from "../state/user";
import ThemeProvider from "../components/ThemeProvider";

const queryClient = new QueryClient();

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
          <main className="flex-1 overflow-y-auto">
            <Toaster position="top-right" />
            <Component {...pageProps} />
          </main>
        </div>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
