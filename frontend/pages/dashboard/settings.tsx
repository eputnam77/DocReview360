import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUserStore } from "@/state/user";

interface Visibility {
  stats: boolean;
  status: boolean;
  activity: boolean;
  logs: boolean;
}

export default function DashboardSettingsPage() {
  const [vis, setVis] = useState<Visibility>({
    stats: true,
    status: true,
    activity: true,
    logs: true,
  });
  const username = useUserStore((s) => s.username);

  useEffect(() => {
    if (!username) return;
    fetch("/dashboard/visibility", { headers: { "X-User": username } })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setVis(d))
      .catch(() => {});
  }, [username]);

  const toggle = (k: keyof Visibility) =>
    setVis((v) => ({ ...v, [k]: !v[k] }));

  const save = () => {
    if (!username) return;
    fetch("/dashboard/visibility", {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-User": username },
      body: JSON.stringify(vis),
    }).catch(() => {});
  };

  return (
    <div className="p-8 space-y-4">
      <h1 className="text-xl font-bold">Dashboard Settings</h1>
      <Card>
        <CardHeader>
          <CardTitle>Widget Visibility</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {Object.keys(vis).map((k) => (
            <label key={k} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={vis[k as keyof Visibility]}
                onChange={() => toggle(k as keyof Visibility)}
              />
              <span className="capitalize">{k}</span>
            </label>
          ))}
        </CardContent>
      </Card>
      <Button onClick={save}>Save</Button>
    </div>
  );
}
