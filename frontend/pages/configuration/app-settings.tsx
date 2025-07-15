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
];

export default function AppSettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    fetch("/api/config")
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

  const saveEdit = (id: string) => {
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

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">App Settings</h1>
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
        />
        <Input
          placeholder="Value"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          className="max-w-xs"
        />
        <Button type="submit" size="sm">
          Add
        </Button>
      </form>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Key</TableHead>
            <TableHead>Value</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {settings.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-mono">{s.key}</TableCell>
              <TableCell className="min-w-[150px]">
                {editingId === s.id ? (
                  <Input
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="h-8"
                  />
                ) : (
                  s.value
                )}
              </TableCell>
              <TableCell className="w-28">
                {editingId === s.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(s.id)}>
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
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No settings defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
