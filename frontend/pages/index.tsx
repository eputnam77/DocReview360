// pages/index.tsx or app/page.tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/router";
import { API, authenticatedFetch } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Ping the API to ensure backend is reachable before redirecting
    authenticatedFetch(`${API}/ping`).catch(() => {
      /* ignore network errors */
    });
    // Redirect to login page
    router.push("/login");
  }, [router]);

  // Show nothing while redirecting
  return null;
}
