// pages/index.tsx or app/page.tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/router";
export default function Home() {
    const router = useRouter();
    useEffect(() => {
        // Ping the API to ensure backend is reachable before redirecting
        fetch("/ping").catch(() => {
            /* ignore network errors */
        });
        // Redirect to login page
        router.push("/login");
    }, [router]);
    // Show nothing while redirecting
    return null;
}
