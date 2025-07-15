import type { AppProps } from "next/app";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "../styles/globals.css";
import Sidebar from "../components/workflow/Sidebar";
import { useEffect } from "react";
import { useUserStore } from "../state/user";

const queryClient = new QueryClient();

export default function App({ Component, pageProps }: AppProps) {
  const init = useUserStore((s) => s.initialize);
  useEffect(() => {
    void init();
  }, [init]);
  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex min-h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Component {...pageProps} />
        </main>
      </div>
    </QueryClientProvider>
  );
}
