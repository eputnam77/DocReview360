import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useDashboardVisibility } from "@/state/visibility";
export default function DashboardSettingsPage() {
    const { vis, setVis, save } = useDashboardVisibility();
    const toggle = (k) => setVis((v) => ({ ...v, [k]: !v[k] }));
    return (<div className="p-8 space-y-4">
      <h1 className="text-xl font-bold">Dashboard Settings</h1>
      <Card>
        <CardHeader>
          <CardTitle>Widget Visibility</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {Object.keys(vis).map((k) => (<label key={k} className="flex items-center gap-2">
              <input type="checkbox" checked={vis[k]} onChange={() => toggle(k)}/>
              <span className="capitalize">{k}</span>
            </label>))}
        </CardContent>
      </Card>
      <Button onClick={save}>Save</Button>
    </div>);
}
