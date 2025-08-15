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

// --- System role choices, update as needed ---
const ROLE_CHOICES = [
  { id: "admin", label: "Administrator" },
  { id: "pm", label: "Program/Project Manager" },
  { id: "user", label: "User (Contributor)" },
  { id: "reviewer", label: "Reviewer" },
  { id: "editor", label: "Editor" },
  { id: "viewer", label: "Viewer (Read-only)" },
];

interface User {
  id: string;
  username: string;
  roles: string[]; // Now supports multiple roles
}


export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [newName, setNewName] = useState("");
  const [newRoles, setNewRoles] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editRoles, setEditRoles] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API}/users`)
      .then((r) => (r.ok ? r.json() : []))
        .then((data: any[]) =>
          setUsers(
            data.length
              ? data.map((u) => ({
                  id: u.id || u.username,
                  username: u.username,
                  roles: Array.isArray(u.roles)
                    ? u.roles
                    : typeof u.role === "string"
                    ? [u.role]
                    : [],
                }))
              : []
          )
        )
        .catch(() => setUsers([]));
  }, []);

  const addUser = () => {
    if (!newName.trim()) return;
    setUsers([
      ...users,
      {
        id: "u-" + Date.now().toString(),
        username: newName.trim(),
        roles: newRoles.length ? newRoles : [],
      },
    ]);
    setNewName("");
    setNewRoles([]);
  };

  const removeUser = (id: string) =>
    setUsers(users.filter((u) => u.id !== id));

  const startEdit = (u: User) => {
    setEditingId(u.id);
    setEditName(u.username);
    setEditRoles(u.roles || []);
  };

  const saveEdit = (id: string) => {
    if (!editName.trim()) return;
    setUsers(
      users.map((u) =>
        u.id === id
          ? { ...u, username: editName.trim(), roles: editRoles }
          : u,
      ),
    );
    setEditingId(null);
    setEditName("");
    setEditRoles([]);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditRoles([]);
  };

  // --- Render ---
  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold mb-2">User Management</h1>
      <div className="text-gray-600 text-sm mb-4">
        Add users and assign one or more roles. Each role determines the user's access and permissions within the system.
      </div>
      <form
        className="flex flex-wrap gap-2 items-end"
        onSubmit={(e) => {
          e.preventDefault();
          addUser();
        }}
      >
        <Input
          placeholder="Username"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="max-w-xs"
        />
        <div>
          <label className="block text-xs font-semibold mb-1">Role(s)</label>
          <select
            multiple
            value={newRoles}
            onChange={(e) => {
              const options = Array.from(e.target.selectedOptions, o => o.value);
              setNewRoles(options);
            }}
            className="border rounded p-1 min-w-[180px] h-[38px]"
          >
            {ROLE_CHOICES.map(r => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" size="sm">
          Add
        </Button>
      </form>
      <Table caption="Users">
        <TableHeader>
          <TableRow>
            <TableHead>Username</TableHead>
            <TableHead>Roles</TableHead>
            <TableHead>Edit</TableHead>
            <TableHead>Remove</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((u) => (
            <TableRow key={u.id}>
              <TableCell className="min-w-[150px]">
                {editingId === u.id ? (
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="h-8"
                  />
                ) : (
                  u.username
                )}
              </TableCell>
              <TableCell className="min-w-[200px]">
                {editingId === u.id ? (
                  <select
                    multiple
                    value={editRoles}
                    onChange={(e) => {
                      const options = Array.from(e.target.selectedOptions, o => o.value);
                      setEditRoles(options);
                    }}
                    className="border rounded p-1 min-w-[180px] h-[38px]"
                  >
                    {ROLE_CHOICES.map(r => (
                      <option key={r.id} value={r.id}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  u.roles && u.roles.length
                    ? u.roles
                        .map(
                          (rid) =>
                            ROLE_CHOICES.find((r) => r.id === rid)?.label || rid,
                        )
                        .join(", ")
                    : <span className="text-gray-400">—</span>
                )}
              </TableCell>
              <TableCell className="w-28">
                {editingId === u.id ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(u.id)}>
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
                    onClick={() => startEdit(u)}
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
                  onClick={() => removeUser(u.id)}
                  title="Remove"
                  aria-label="Remove"
                >
                  <Trash className="w-4 h-4 text-red-600" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {users.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No users defined.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <div className="mt-6 text-xs text-gray-500 max-w-2xl">
        <strong>Tip:</strong> Each user can have one or more roles, which control their access throughout the system.
        Assign roles carefully. Use the Permissions page to define what each role can do.
      </div>
    </div>
  );
}
