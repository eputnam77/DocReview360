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

interface Permission {
  id: string;
  role: string;
  action: string;
  allowed: boolean;
}

const DEMO_PERMISSIONS: Permission[] = [
  { id: "admin-delete_project", role: "admin", action: "delete_project", allowed: true },
  { id: "pm-delete_project", role: "pm", action: "delete_project", allowed: false },
];

export default function PermissionsPage() {
  const [perms, setPerms] = useState<Permission[]>([]);
  const [newRole, setNewRole] = useState("");
  const [newAction, setNewAction] = useState("");
  const [newAllowed, setNewAllowed] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editAllowed, setEditAllowed] = useState(true);

  useEffect(() => {
    fetch("/api/rbac")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          const rows: Permission[] = [];
          for (const [role, actions] of Object.entries<any>(data)) {
            for (const [action, allowed] of Object.entries(actions as any)) {
              rows.push({
                id: `${role}-${action}`,
                role,
                action,
                allowed: !!allowed,
              });
            }
          }
          setPerms(rows);
        } else {
          setPerms(DEMO_PERMISSIONS);
        }
      })
      .catch(() => setPerms(DEMO_PERMISSIONS));
  }, []);

  const addPermission = () => {
    if (!newRole.trim() || !newAction.trim()) return;
    setPerms([
      ...perms,
      {
        id: `${newRole}-${newAction}`,
        role: newRole.trim(),
        action: newAction.trim(),
        allowed: newAllowed,
      },
    ]);
    setNewRole("");
    setNewAction("");
    setNewAllowed(true);
  };

  const removePermission = (id: string) =>
    setPerms(perms.filter((p) => p.id !== id));

  const startEdit = (p: Permission) => {
    setEditingId(p.id);
    setEditAllowed(p.allowed);
  };

  const saveEdit = (id: string) => {
    setPerms(perms.map((p) => (p.id === id ? { ...p, allowed: editAllowed } : p)));
    setEditingId(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Permissions</h1>
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          addPermission();
        }}
      >
        <Input
          placeholder="Role"
          value={newRole}
          onChange={(e) => setNewRole(e.target.value)}
          className="max-w-xs"
        />
        <Input
          placeholder="Action"
          value={newAction}
          onChange={(e) => setNewAction(e.target.value)}
          className="max-w-xs"
        />
        <label className="flex items-center gap-1 text-sm">
          <input
            type="checkbox"
            checked={newAllowed}
            onChange={(e) => setNewAllowed(e.target.checked)}
          />
          Allowed
        </label>
        <Button type="submit" size="sm">
          Add
        </Button>
      </form>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Role</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Allowed</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {perms.map((p) => (
            <TableRow key={p.id}>
              <TableCell className="font-mono">{p.role}</TableCell>
              <TableCell>{p.action}</TableCell>
              <TableCell className="text-center">
                {editingId === p.id ? (
                  <input
                    type="checkbox"
                    checked={editAllowed}
                    onChange={(e) => setEditAllowed(e.target.checked)}
                  />
                ) : p.allowed ? (
                  "Yes"
                ) : (
                  "No"
                )}
              </TableCell>
              <TableCell className="w-28">
                {editingId === p.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(p.id)}>
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
                    onClick={() => startEdit(p)}
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
                  onClick={() => removePermission(p.id)}
                  title="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {perms.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-gray-400 py-6">
                No permissions defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
