import React, { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { Pencil, Trash } from "lucide-react";
import { API } from "@/lib/api";

const DATABASES = ["postgres", "mysql", "sqlite"];
const EDITORS = ["tiptap", "onlyoffice", "xml", "word"];
const CMS_OPTIONS = ["none", "local"];

const SETTING_DESCRIPTIONS: Record<string, string> = {
  database: "The backend database used by the app.",
  editor: "The default document editor for users.",
  cms: "CMS integration for content storage.",
  auth: "Authentication provider (e.g., OIDC, SAML, local).",
  host: "The hostname or IP where the server runs.",
  port: "The network port for the server.",
  debug: "Enable or disable debug mode.",
  email: "System notification sender email.",
  upload_max_mb: "Max file upload size (in MB).",
};

const SELECT_OPTIONS: Record<string, { label: string; value: string }[]> = {
  editor: [
    { label: "TipTap", value: "tiptap" },
    { label: "Word", value: "word" },
  ],
  database: [
    { label: "SQLite", value: "sqlite" },
    { label: "Postgres", value: "postgres" },
    { label: "MySQL", value: "mysql" },
    { label: "SQL Server", value: "sqlserver" },
  ],
  auth: [
    { label: "OIDC", value: "oidc" },
    { label: "SAML", value: "saml" },
    { label: "Local", value: "local" },
  ],
  cms: [
    { label: "None", value: "none" },
    { label: "SharePoint", value: "sharepoint" },
    { label: "Confluence", value: "confluence" },
    { label: "Google Drive", value: "gdrive" },
  ],
  debug: [
    { label: "True", value: "true" },
    { label: "False", value: "false" },
  ],
};

const EXTRA_INTEGRATIONS = [
  { label: "Workflow Engine", value: "Camunda" },
  { label: "Signatures", value: "Documenso" },
  { label: "Search Engine", value: "OpenSearch" },
  { label: "Analytics", value: "Metabase" },
  { label: "Object Storage", value: "MinIO/S3" },
  { label: "AI Helpers", value: "AWS Bedrock" },
  { label: "GitHub Sync", value: "Enabled" },
];

const DEMO_CONFIG: Record<string, string | number | boolean> = {
  database: "sqlite",
  editor: "tiptap",
  cms: "none",
  auth: "oidc",
  host: "localhost",
  port: 8000,
  debug: false,
  email: "noreply@example.com",
  upload_max_mb: 5,
};

export default function IntegrationsPage() {
  const [config, setConfig] = useState<Record<string, string | number | boolean>>(DEMO_CONFIG);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    fetch(`${API}/config`)
      .then((r) => (r.ok ? r.json() : DEMO_CONFIG))
      .then((data) =>
        setConfig(Object.keys(data || {}).length ? data : DEMO_CONFIG),
      )
      .catch(() => setConfig(DEMO_CONFIG));
  }, []);

  const update = (key: string, value: string | number | boolean) => {
    if (key === "database" && config.database !== value) {
      const confirmed = window.confirm(
        "Switching the database may remove existing content. Continue?",
      );
      if (!confirmed) return;
    }
    setConfig({ ...config, [key]: value });
  };

  const handleSave = async () => {
    try {
      const resp = await fetch(`${API}/config`, {
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
    } catch {
      alert("Failed to save configuration (offline demo)");
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
      <div className="pt-6 space-y-4">
        <h2 className="text-lg font-semibold">All Settings</h2>
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!newKey.trim()) return;
            setConfig({ ...config, [newKey]: newValue });
            setNewKey("");
            setNewValue("");
          }}
        >
          <Input
            placeholder="Setting Key"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            className="max-w-xs"
            list="setting-key-list"
          />
          <datalist id="setting-key-list">
            {Object.keys(SETTING_DESCRIPTIONS)
              .filter((k) => !(k in config))
              .map((k) => (
                <option value={k} key={k} />
              ))}
          </datalist>
          {SELECT_OPTIONS[newKey] ? (
            <select
              className="border rounded px-2 py-1 max-w-xs"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
            >
              <option value="">Choose…</option>
              {SELECT_OPTIONS[newKey].map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ) : (
            <Input
              placeholder="Value"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              className="max-w-xs"
            />
          )}
          <Button type="submit" size="sm">
            Add
          </Button>
        </form>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Key</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Value</TableHead>
              <TableHead>Edit</TableHead>
              <TableHead>Remove</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Object.entries(config).map(([k, v]) => (
              <TableRow key={k}>
                <TableCell className="font-mono">{k}</TableCell>
                <TableCell className="max-w-xs text-xs text-gray-500">
                  {SETTING_DESCRIPTIONS[k] || (
                    <span className="text-gray-400">—</span>
                  )}
                </TableCell>
                <TableCell className="min-w-[150px]">
                  {editingId === k ? (
                    SELECT_OPTIONS[k] ? (
                      <select
                        className="border rounded px-2 py-1 max-w-xs"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                      >
                        <option value="">Choose…</option>
                        {SELECT_OPTIONS[k].map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="h-8"
                      />
                    )
                  ) : (
                    <span>
                      {SELECT_OPTIONS[k]
                        ? SELECT_OPTIONS[k].find((opt) => opt.value === String(v))
                            ?.label || String(v)
                        : String(v)}
                    </span>
                  )}
                </TableCell>
                <TableCell className="w-28">
                  {editingId === k ? (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => {
                          setConfig({ ...config, [k]: editValue });
                          setEditingId(null);
                          setEditValue("");
                        }}
                      >
                        Save
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditingId(null);
                          setEditValue("");
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setEditingId(k);
                        setEditValue(String(v));
                      }}
                      title="Edit"
                    >
                      <Pencil className="w-4 h-4" />
                    </Button>
                  )}
                </TableCell>
                <TableCell className="w-20">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      const copy = { ...config };
                      delete copy[k];
                      setConfig(copy);
                    }}
                    title="Remove"
                  >
                    <Trash className="w-4 h-4 text-red-600" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {Object.keys(config).length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                  No settings defined.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
