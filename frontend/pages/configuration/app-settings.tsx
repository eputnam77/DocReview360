import React, { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Pencil, Trash } from "lucide-react";
import { API } from "@/lib/api";

// Known keys and value options for select fields and toggles
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
    { label: "Toast", value: "toast" },
    { label: "Codex", value: "codex" },
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

interface Setting {
  id: string;
  key: string;
  value: string;
}

const DEMO_SETTINGS: Setting[] = [
  { id: "database", key: "database", value: "sqlite" },
  { id: "editor", key: "editor", value: "tiptap" },
  { id: "cms", key: "cms", value: "none" },
  { id: "auth", key: "auth", value: "oidc" },
  { id: "host", key: "host", value: "127.0.0.1" },
  { id: "port", key: "port", value: "8000" },
  { id: "debug", key: "debug", value: "false" },
  { id: "email", key: "email", value: "admin@example.com" },
  { id: "upload_max_mb", key: "upload_max_mb", value: "25" },
];

export default function AppSettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    fetch(`${API}/config`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          const entries = Object.entries(data).map(([k, v]) => ({
            id: k,
            key: k,
            value: String(v),
          }));
          setSettings(entries);
        } else {
          setSettings(DEMO_SETTINGS);
        }
      })
      .catch(() => setSettings(DEMO_SETTINGS));
  }, []);

  const addSetting = () => {
    if (!newKey.trim()) return;
    setSettings([
      ...settings,
      { id: newKey, key: newKey, value: newValue },
    ]);
    setNewKey("");
    setNewValue("");
  };

  const removeSetting = (id: string) =>
    setSettings(settings.filter((s) => s.id !== id));

  const startEdit = (s: Setting) => {
    setEditingId(s.id);
    setEditValue(s.value);
  };

  const saveEdit = (id: string, key: string) => {
    setSettings(
      settings.map((s) => (s.id === id ? { ...s, value: editValue } : s)),
    );
    setEditingId(null);
    setEditValue("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue("");
  };

  // Optional: Only allow adding keys that aren't already used
  const usedKeys = settings.map((s) => s.key);

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">App Settings</h1>
      <div className="text-gray-600 text-sm mb-4 max-w-2xl">
        <p>
          System configuration is loaded during app startup. <br />
          Update settings to change default editor, authentication, database, and more. <br />
          <b>Tip:</b> Use dropdowns for recommended values. Some changes may require a restart.
        </p>
      </div>
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          addSetting();
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
            .filter((k) => !usedKeys.includes(k))
            .map((k) => (
              <option value={k} key={k} />
            ))}
        </datalist>
        {/* Value input adapts to common keys */}
        {SELECT_OPTIONS[newKey] ? (
          <select
            className="border rounded px-2 py-1 max-w-xs"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
          >
            <option value="">Choose…</option>
            {SELECT_OPTIONS[newKey].map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
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
          {settings.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-mono">{s.key}</TableCell>
              <TableCell className="max-w-xs text-xs text-gray-500">
                {SETTING_DESCRIPTIONS[s.key] || <span className="text-gray-400">—</span>}
              </TableCell>
              <TableCell className="min-w-[150px]">
                {editingId === s.id ? (
                  SELECT_OPTIONS[s.key] ? (
                    <select
                      className="border rounded px-2 py-1 max-w-xs"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                    >
                      <option value="">Choose…</option>
                      {SELECT_OPTIONS[s.key].map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
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
                    {SELECT_OPTIONS[s.key]
                      ? SELECT_OPTIONS[s.key].find((opt) => opt.value === s.value)?.label || s.value
                      : s.value}
                  </span>
                )}
              </TableCell>
              <TableCell className="w-28">
                {editingId === s.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(s.id, s.key)}>
                      Save
                    </Button>
                    <Button size="sm" variant="ghost" onClick={cancelEdit}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => startEdit(s)}
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
                  onClick={() => removeSetting(s.id)}
                  title="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {settings.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No settings defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <div className="mt-4 text-xs text-gray-500 max-w-2xl">
        <strong>Common settings:</strong> database, editor, cms, auth, host, port, debug, email, upload_max_mb<br />
        <strong>Tip:</strong> Some changes require a restart to take effect.
      </div>
    </div>
  );
}
