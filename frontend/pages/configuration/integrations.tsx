import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { API } from "@/lib/api";
import { Pencil, Trash } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";

const CMS_OPTIONS = [
  { label: "None", value: "none" },
  { label: "Local", value: "local" },
  { label: "SharePoint", value: "sharepoint" },
  { label: "Confluence", value: "confluence" },
  { label: "Google Drive", value: "gdrive" },
] as const;

const integrationOptions = {
  database: [
    { label: "SQLite", value: "sqlite" },
    { label: "Postgres", value: "postgres" },
    { label: "MySQL", value: "mysql" },
    { label: "SQL Server", value: "sqlserver" },
  ],
  editor: [
    { label: "TipTap", value: "tiptap" },
    { label: "OnlyOffice", value: "onlyoffice" },
    { label: "XML", value: "xml" },
    { label: "Word", value: "word" },
  ],
  signatureProviders: [
    { label: "Documenso", value: "documenso" },
    { label: "Local", value: "local" },
  ],
} as const;

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
  editor: integrationOptions.editor,
  database: integrationOptions.database,
  auth: [
    { label: "OIDC", value: "oidc" },
    { label: "SAML", value: "saml" },
    { label: "Local", value: "local" },
  ],
  cms: CMS_OPTIONS,
  debug: [
    { label: "True", value: "true" },
    { label: "False", value: "false" },
  ],
};


const DEFAULT_CONFIG: Record<string, string | number | boolean> = {
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
  const [config, setConfig] =
    useState<Record<string, string | number | boolean>>(DEFAULT_CONFIG);
  const [primaryProvider, setPrimaryProvider] = useState("documenso");
  const [fallbackProvider, setFallbackProvider] = useState("local");
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/config`).then((r) => (r.ok ? r.json() : DEFAULT_CONFIG)),
      fetch(`${API}/signature-provider`).then((r) =>
        r.ok ? r.json() : { primary: "documenso", fallback: "local" },
      ),
    ])
      .then(([cfg, prov]) => {
        setConfig(Object.keys(cfg || {}).length ? cfg : DEFAULT_CONFIG);
        setPrimaryProvider(prov.primary);
        setFallbackProvider(prov.fallback);
      })
      .catch((err) => {
        console.error("Failed to fetch integrations", err);
        toast.error("Failed to load integration settings; using defaults.");
        setConfig(DEFAULT_CONFIG);
        setPrimaryProvider("documenso");
        setFallbackProvider("local");
        setLoadError("Failed to load integration settings; using defaults.");
      });
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
      const sigResp = await fetch(`${API}/signature-provider`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ primary: primaryProvider, fallback: fallbackProvider }),
      });
      if (resp.ok && sigResp.ok) {
        toast.success(
          "Configuration saved. Changing integrations may require a restart and could cause data loss.",
        );
      } else {
        toast.error("Failed to save configuration");
      }
    } catch {
      toast.error("Failed to save configuration");
    }
  };

  const getLabel = (
    opts: readonly { label: string; value: string }[],
    value: string | number | boolean | null | undefined,
  ) => opts.find((opt) => opt.value === String(value))?.label || String(value ?? "");

  const extraIntegrations = [
    {
      label: "Database",
      value: getLabel(integrationOptions.database, config.database),
    },
    {
      label: "Document Editor",
      value: getLabel(integrationOptions.editor, config.editor),
    },
    {
      label: "CMS Integration",
      value: getLabel(CMS_OPTIONS, config.cms),
    },
    {
      label: "Auth Provider",
      value: getLabel(SELECT_OPTIONS.auth, config.auth),
    },
    {
      label: "Signature Provider",
      value: getLabel(
        integrationOptions.signatureProviders,
        primaryProvider,
      ),
    },
    ...(fallbackProvider
      ? [
          {
            label: "Fallback Signature Provider",
            value: getLabel(
              integrationOptions.signatureProviders,
              fallbackProvider,
            ),
          },
        ]
      : []),
  ];

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
      {loadError && (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
          {loadError}
        </div>
      )}
      <p className="text-sm text-gray-500">
        Changing these options might delete or recreate data. Proceed with
        caution.
      </p>
      <div className="space-y-4 max-w-sm">
        <div className="space-y-2">
          <Label>Database</Label>
          <Select
            value={String(config.database)}
            onValueChange={(v) => update("database", v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a database" />
            </SelectTrigger>
            <SelectContent>
              {integrationOptions.database.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Document Editor</Label>
          <Select
            value={String(config.editor)}
            onValueChange={(v) => update("editor", v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select an editor" />
            </SelectTrigger>
            <SelectContent>
              {integrationOptions.editor.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>CMS Integration</Label>
          <Select value={String(config.cms)} onValueChange={(v) => update("cms", v)}>
            <SelectTrigger>
              <SelectValue placeholder="Select CMS option" />
            </SelectTrigger>
            <SelectContent>
              {CMS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Signature Provider</Label>
          <Select
            value={primaryProvider}
            onValueChange={(v) => setPrimaryProvider(v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {integrationOptions.signatureProviders.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Fallback Signature Provider</Label>
          <Select
            value={fallbackProvider}
            onValueChange={(v) => setFallbackProvider(v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select fallback" />
            </SelectTrigger>
            <SelectContent>
              {integrationOptions.signatureProviders.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Auth Provider</Label>
          <Input
            value={String(config.auth)}
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
          {extraIntegrations.map((item) => (
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
            let value: string | number | boolean = newValue;
            if (newValue === "true" || newValue === "false") {
              value = newValue === "true";
            } else if (newValue !== "" && !isNaN(Number(newValue))) {
              value = Number(newValue);
            }
            setConfig({ ...config, [newKey]: value });
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
        <Table caption="Integrations">
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
                          let value: string | number | boolean = editValue;
                          const current = config[k];
                          if (typeof current === "boolean") {
                            value = editValue === "true";
                          } else if (typeof current === "number") {
                            const num = Number(editValue);
                            value = isNaN(num) ? editValue : num;
                          }
                          setConfig({ ...config, [k]: value });
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
                      aria-label="Edit"
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
                    aria-label="Remove"
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
