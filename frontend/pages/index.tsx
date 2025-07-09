// pages/index.tsx or app/page.tsx
"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useCounterStore } from "@/state/useStore";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function Home() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["ping"],
    queryFn: () => fetch("/api/ping").then((r) => r.text()),
  });
  const count = useCounterStore((s) => s.count);
  const increment = useCounterStore((s) => s.increment);

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-50 to-white">
      <Card className="max-w-md w-full shadow-xl">
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-center text-indigo-700">
            DocuFlow Demo
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <p>
            {isLoading
              ? "Loading ping..."
              : error
                ? "Failed to load ping."
                : data}
          </p>
          <p className="text-gray-600">
            Current count: <span className="font-mono font-bold">{count}</span>
          </p>
        </CardContent>
        <CardFooter className="flex justify-center">
          <Button onClick={increment} variant="default" className="gap-2">
            Increment
          </Button>
        </CardFooter>
      </Card>
    </main>
  );
}
