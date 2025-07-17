import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface DashboardEntry {
  project: string;
  status: string;
}

export default function ManagerDashboardPage() {
  const [items, setItems] = useState<DashboardEntry[]>([]);

  useEffect(() => {
    fetch("/dashboard/manager")
      .then((r) => (r.ok ? r.json() : []))
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold mb-4">Manager Dashboard</h1>
      {items.map((it) => (
        <Card key={it.project}>
          <CardHeader>
            <CardTitle>{it.project}</CardTitle>
          </CardHeader>
          <CardContent className="text-gray-600">{it.status}</CardContent>
        </Card>
      ))}
      {items.length === 0 && <p>No projects found.</p>}
    </div>
  );
}
