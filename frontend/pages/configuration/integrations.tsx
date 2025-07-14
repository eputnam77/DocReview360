import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

const DATABASES = ["postgres", "mysql", "sqlite"];
const EDITORS = ["tiptap", "toast", "onlyoffice", "xml", "codex", "word"];
const CMS_OPTIONS = ["none", "local"];

const EXTRA_INTEGRATIONS = [
  { label: "Workflow Engine", value: "Camunda" },
  { label: "Signatures", value: "Documenso" },
  { label: "Search Engine", value: "OpenSearch" },
  { label: "Analytics", value: "Metabase" },
  { label: "Object Storage", value: "MinIO/S3" },
  { label: "AI Helpers", value: "AWS Bedrock" },
  { label: "GitHub Sync", value: "Enabled" },
];

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
    fetch("/config")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setConfig(data);
      })
      .catch(() => {});
  }, []);

  const update = (key: keyof Config, value: string | number | boolean) => {
    if (!config) return;
    if (key === "database" && config.database !== value) {
      const confirmed = window.confirm(
        "Switching the database may remove existing content. Continue?",
      );
      if (!confirmed) return;
    }
    setConfig({ ...config, [key]: value } as Config);
  };

  const handleSave = async () => {
    if (!config) return;
    const resp = await fetch("/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (resp.ok) {
      alert(
        "Configuration saved. Changing integrations may require a restart and could cause data loss.",
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
        <div className="space-y-2">
          <Label>Database</Label>
          <Select
            value={config.database}
            onValueChange={(v) => update("database", v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a database" />
            </SelectTrigger>
            <SelectContent>
              {DATABASES.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Document Editor</Label>
          <Select
            value={config.editor}
            onValueChange={(v) => update("editor", v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select an editor" />
            </SelectTrigger>
            <SelectContent>
              {EDITORS.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>CMS Integration</Label>
          <Select value={config.cms} onValueChange={(v) => update("cms", v)}>
            <SelectTrigger>
              <SelectValue placeholder="Select CMS option" />
            </SelectTrigger>
            <SelectContent>
              {CMS_OPTIONS.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Auth Provider</Label>
          <Input
            value={config.auth}
            readOnly
            disabled
            className="bg-gray-100"
          />
          <p className="text-xs text-gray-500">Change via CLI if required</p>
        </div>
        <Button onClick={handleSave}>Save Changes</Button>
      </div>
      <div className="pt-6">
        <h2 className="text-lg font-semibold mb-2">Additional Integrations</h2>
        <ul className="space-y-1 text-sm list-disc ml-4">
          {EXTRA_INTEGRATIONS.map((item) => (
            <li key={item.label}>
              <span className="font-medium">{item.label}:</span> {item.value}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
