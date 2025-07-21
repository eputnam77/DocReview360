import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface DashboardEntry {
  id: string;
  name: string;
  priority: number;
  phase?: string | null;
  docs: number;
  pending_approvals: number;
}

export default function ManagerDashboardPage() {
  const [items, setItems] = useState<DashboardEntry[]>([]);

  useEffect(() => {
    fetch("/reports/dashboard")
      .then((r) => (r.ok ? r.json() : []))
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold mb-4">Manager Dashboard</h1>
      {items.map((it) => (
        <Card key={it.id} className="hover:bg-muted cursor-pointer" onClick={() => window.location.href = `/dashboard/project/${it.id}` }>
          <CardHeader>
            <CardTitle>{it.name}</CardTitle>
          </CardHeader>
          <CardContent className="text-gray-600 space-y-1">
            <p>Phase: {it.phase ?? "-"}</p>
            <p>Documents: {it.docs}</p>
            <p>Pending approvals: {it.pending_approvals}</p>
          </CardContent>
        </Card>
      ))}
      {items.length === 0 && <p>No projects found.</p>}
    </div>
  );
}
