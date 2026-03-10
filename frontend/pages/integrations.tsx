import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, Button, Label } from "@/components";
import { authenticatedFetch } from "@/lib/api";
import { toast } from "react-hot-toast";

type Config = {
  database: string;
  database_url?: string | null;
  editor: string;
  cms: string;
  auth: string;
  host: string;
  port: number;
  debug: boolean;
  ai_auto_assign_writers: boolean;
};

const DEFAULTS: Config = {
  database: "sqlite",
  editor: "tiptap",
  cms: "none",
  auth: "oidc",
  host: "127.0.0.1",
  port: 8000,
  debug: false,
  ai_auto_assign_writers: false,
};

export default function IntegrationsPage() {
  const [config, setConfig] = useState<Config>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    authenticatedFetch(`/config`)
      .then((r) => (r.ok ? r.json() : DEFAULTS))
      .then((data: Partial<Config>) => {
        setConfig({ ...DEFAULTS, ...data });
      })
      .catch(() => setConfig(DEFAULTS))
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      // PUT full config back, preserving other fields
      await authenticatedFetch(`/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      toast.success("Configuration saved");
    } catch {
      toast.error("Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-8">Loading configuration…</div>;

  return (
    <div className="p-8 max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Integrations & Configuration</h1>
      <p className="text-gray-600 text-sm">Manage optional features and integrations.</p>

      <Card>
        <CardHeader>
          <CardTitle>AI Auto-Assignment</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3">
            <input
              id="ai-auto-assign"
              type="checkbox"
              checked={config.ai_auto_assign_writers}
              onChange={(e) => setConfig((c) => ({ ...c, ai_auto_assign_writers: e.target.checked }))}
              className="mr-2"
            />
            <Label htmlFor="ai-auto-assign" className="font-normal">
              Allow AI to auto-assign Technical Writers to projects
            </Label>
          </div>
          <div className="text-xs text-gray-500">
            When disabled, AI will not assign Technical Writers automatically. Manual assignment only.
          </div>
          <div className="pt-2">
            <Button variant="primary" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

