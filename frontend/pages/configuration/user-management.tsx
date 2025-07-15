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

interface User {
  id: string;
  username: string;
  role?: string;
}

const DEMO_USERS: User[] = [
  { id: "u1", username: "admin", role: "Administrator" },
  { id: "u2", username: "jane", role: "Editor" },
];

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editRole, setEditRole] = useState("");

  useEffect(() => {
    fetch("/api/users")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) =>
        setUsers(
          data.length
            ? data.map((u) => ({
                id: u.id || u.username,
                username: u.username,
                role: u.role,
              }))
            : DEMO_USERS,
        )
      )
      .catch(() => setUsers(DEMO_USERS));
  }, []);

  const addUser = () => {
    if (!newName.trim()) return;
    setUsers([
      ...users,
      {
        id: "u-" + Date.now().toString(),
        username: newName.trim(),
        role: newRole.trim() || undefined,
      },
    ]);
    setNewName("");
    setNewRole("");
  };

  const removeUser = (id: string) =>
    setUsers(users.filter((u) => u.id !== id));

  const startEdit = (u: User) => {
    setEditingId(u.id);
    setEditName(u.username);
    setEditRole(u.role || "");
  };

  const saveEdit = (id: string) => {
    if (!editName.trim()) return;
    setUsers(
      users.map((u) =>
        u.id === id
          ? { ...u, username: editName.trim(), role: editRole.trim() || undefined }
          : u,
      ),
    );
    setEditingId(null);
    setEditName("");
    setEditRole("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditRole("");
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">User Management</h1>
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
        <Input
          placeholder="Role"
          value={newRole}
          onChange={(e) => setNewRole(e.target.value)}
          className="max-w-xs"
        />
        <Button type="submit" size="sm">
          Add
        </Button>
      </form>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Username</TableHead>
            <TableHead>Role</TableHead>
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
              <TableCell className="min-w-[150px]">
                {editingId === u.id ? (
                  <Input
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    className="h-8"
                  />
                ) : (
                  u.role || <span className="text-gray-400">—</span>
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
    </div>
  );
}
