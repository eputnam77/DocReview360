import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const DATABASES = ["postgres", "mysql", "sqlite"];
const EDITORS = ["tiptap", "toast", "onlyoffice", "xml", "codex", "word"];
const CMS_OPTIONS = ["none", "local"];

interface Config {
  database: string;
  editor: string;
  cms: string;
  auth: string;
  host: string;
  port: number;
  debug: boolean;
}

export default function IntegrationsPage() {
  const [config, setConfig] = useState<Config | null>(null);

  useEffect(() => {
    fetch("/api/config")
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data) setConfig(data);
      })
      .catch(() => {});
  }, []);

  const update = (key: keyof Config, value: string | number | boolean) => {
    if (!config) return;
    setConfig({ ...config, [key]: value } as Config);
  };

  const handleSave = async () => {
    if (!config) return;
    const resp = await fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (resp.ok) {
      alert(
        "Configuration saved. Changing integrations may require a restart and could cause data loss."
      );
    } else {
      alert("Failed to save configuration");
    }
  };

  if (!config) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Integrations</h1>
      <p className="text-sm text-gray-500">
        Changing these options might delete or recreate data. Proceed with
        caution.
      </p>
      <div className="space-y-4 max-w-sm">
        <div>
          <label className="block text-sm font-medium">Database</label>
          <select
            value={config.database}
            onChange={e => update("database", e.target.value)}
            className="mt-1 border rounded px-2 py-1 w-full"
          >
            {DATABASES.map(opt => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Document Editor</label>
          <select
            value={config.editor}
            onChange={e => update("editor", e.target.value)}
            className="mt-1 border rounded px-2 py-1 w-full"
          >
            {EDITORS.map(opt => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">CMS Integration</label>
          <select
            value={config.cms}
            onChange={e => update("cms", e.target.value)}
            className="mt-1 border rounded px-2 py-1 w-full"
          >
            {CMS_OPTIONS.map(opt => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={handleSave}>Save Changes</Button>
      </div>
    </div>
  );
}

