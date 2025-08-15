"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { useRouter } from "next/router";

interface ReviewCycle {
  id: string;
  name: string;
  commentCount: number;
  lastActivity: string;
}

const cycles: ReviewCycle[] = [
  { id: "1", name: "Cycle 1", commentCount: 0, lastActivity: "—" },
];

export default function ReviewListPage() {
  const router = useRouter();
  const { id } = router.query;

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-2xl font-semibold">Review cycles</h1>
      {cycles.map((c) => (
        <Card key={c.id}>
          <CardHeader>
            <CardTitle>{c.name}</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-between items-center text-sm">
            <span>
              {c.commentCount} comments · Last activity {c.lastActivity}
            </span>
            <Link
              href={`/projects/${id}/reviews/${c.id}`}
              className="text-indigo-600 hover:underline"
            >
              Open
            </Link>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

