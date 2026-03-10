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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pencil, Trash } from "lucide-react";
import { authenticatedFetch } from "@/lib/api";

// --- System role choices, update as needed ---
const ROLE_CHOICES = [
  { id: "admin", label: "Administrator" },
  { id: "manager", label: "Program/Project Manager" },
  { id: "user", label: "User (Contributor)" },
  { id: "reviewer", label: "Reviewer" },
  { id: "editor", label: "Editor" },
  { id: "sme", label: "Subject Matter Expert" },
  { id: "observer", label: "Viewer (Read-only)" },
  { id: "auditor", label: "Auditor" },
  { id: "verifier", label: "Verifier" },
];

interface User {
  id: string;
  username: string;
  roles: string[]; // Now supports multiple roles
}

interface RolePermissionSummary {
  role: string;
  permissions: string[];
  count: number;
  default_permissions: string[];
  default_count: number;
  is_default: boolean;
}

interface ImportError {
  row?: number;
  username?: string;
  error: string;
}

interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: ImportError[];
}

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [newName, setNewName] = useState("");
  const [newRoles, setNewRoles] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [rolePermissions, setRolePermissions] = useState<RolePermissionSummary[]>([]);
  const [editName, setEditName] = useState("");
  const [editRoles, setEditRoles] = useState<string[]>([]);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importMessage, setImportMessage] = useState<string | null>(null);

  const rolePermissionMap = React.useMemo(() => {
    const mapping = new Map<string, RolePermissionSummary>();
    rolePermissions.forEach((role) => mapping.set(role.role, role));
    return mapping;
  }, [rolePermissions]);

  const normalizeUser = (u: any): User => ({
    id: u.id || u.username,
    username: u.username,
    roles: Array.isArray(u.roles)
      ? u.roles
      : typeof u.role === "string"
        ? [u.role]
        : [],
  });

  const loadUsers = async () => {
    try {
      const resp = await authenticatedFetch(`/users`);
      const data = resp.ok ? await resp.json() : [];
      setUsers(Array.isArray(data) ? data.map(normalizeUser) : []);
    } catch (error) {
      console.error("Failed to load users", error);
      setUsers([]);
    }
  };

  const loadRolePermissions = async () => {
    try {
      const resp = await authenticatedFetch(`/rbac/role-permissions`);
      const data = resp.ok ? await resp.json() : [];
      setRolePermissions(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load role permissions", error);
      setRolePermissions([]);
    }
  };

  useEffect(() => {
    void loadUsers();
    void loadRolePermissions();
  }, []);

  const addUser = async () => {
    if (!newName.trim()) return;
    try {
      const resp = await authenticatedFetch(`/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: newName.trim(),
          roles: newRoles.length ? newRoles : [],
        }),
      });
      if (!resp.ok) {
        console.error("Failed to add user");
        return;
      }
      const created = normalizeUser(await resp.json());
      setUsers([...users, created]);
      setNewName("");
      setNewRoles([]);
    } catch (error) {
      console.error("Failed to add user", error);
    }
  };

  const removeUser = async (id: string) => {
    const target = users.find((u) => u.id === id);
    if (!target) return;
    try {
      const resp = await authenticatedFetch(`/users/${encodeURIComponent(target.username)}`, {
        method: "DELETE",
      });
      if (!resp.ok) {
        console.error("Failed to remove user");
        return;
      }
      setUsers(users.filter((u) => u.id !== id));
    } catch (error) {
      console.error("Failed to remove user", error);
    }
  };

  const startEdit = (u: User) => {
    setEditingId(u.id);
    setEditName(u.username);
    setEditRoles(u.roles || []);
  };

  const saveEdit = async (id: string) => {
    if (!editName.trim()) return;
    const target = users.find((u) => u.id === id);
    if (!target) return;
    try {
      const resp = await authenticatedFetch(`/users/${encodeURIComponent(target.username)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: editName.trim(),
          roles: editRoles,
        }),
      });
      if (!resp.ok) {
        console.error("Failed to update user");
        return;
      }
      const updated = normalizeUser(await resp.json());
      setUsers(users.map((u) => (u.id === id ? updated : u)));
      setEditingId(null);
      setEditName("");
      setEditRoles([]);
    } catch (error) {
      console.error("Failed to update user", error);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditRoles([]);
  };

  const importUsers = async () => {
    if (!importFile) {
      setImportMessage("Choose a CSV file to import.");
      return;
    }
    setImportBusy(true);
    setImportMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", importFile);
      const resp = await authenticatedFetch(`/users/import`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const text = await resp.text();
        setImportMessage(text || "Import failed.");
        return;
      }
      const data = (await resp.json()) as ImportResult;
      setImportResult(data);
      setImportFile(null);
      void loadUsers();
    } catch (error) {
      console.error("Failed to import users", error);
      setImportMessage("Import failed. Check the server logs for details.");
    } finally {
      setImportBusy(false);
    }
  };

  // --- Render ---
  return (
    <div className="p-8 space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold mb-2">User Management</h1>
        <div className="text-gray-600 text-sm">
          Add users and assign one or more roles. Each role determines the
          user&#39;s access and permissions within the system.
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Import Users (CSV)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-gray-600">
              Bulk add users with roles. Use a CSV with headers like:
              <span className="ml-1 font-mono text-xs">
                username,roles,display_name,organization,disabled
              </span>
            </p>
            <p className="text-xs text-gray-500">
              Roles should be semicolon-separated (example: Admin;Reviewer).
              The system uses role ids like admin, reviewer, editor.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => {
                  const files = event.target.files;
                  setImportFile(files && files.length > 0 ? files[0] : null);
                }}
                className="text-sm"
              />
              <Button size="sm" onClick={importUsers} disabled={importBusy}>
                {importBusy ? "Importing..." : "Import"}
              </Button>
            </div>
            {importMessage && (
              <div className="text-xs text-red-600">{importMessage}</div>
            )}
            {importResult && (
              <div className="text-xs text-gray-600 space-y-2">
                <div>
                  Imported: {importResult.created} created, {importResult.updated}
                  {" "}
                  updated, {importResult.skipped} skipped.
                </div>
                {importResult.errors?.length > 0 && (
                  <div className="space-y-1">
                    <div className="font-semibold text-red-600">
                      Errors ({importResult.errors.length})
                    </div>
                    <div className="space-y-1">
                      {importResult.errors.slice(0, 5).map((err, idx) => (
                        <div key={`${err.username}-${idx}`}>
                          Row {err.row ?? "?"}: {err.error}
                        </div>
                      ))}
                      {importResult.errors.length > 5 && (
                        <div>See server logs for the full list.</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Auto-Provisioning (SSO/PIV)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-gray-600">
              When enabled, users are created on first login from your identity
              provider (SAML/OIDC). This is the expected model for PIV/CAC.
            </p>
            <div className="flex items-center gap-2 text-sm">
              <input type="checkbox" disabled />
              <span className="text-gray-500">
                Coming soon. Configure your IdP now; wiring will be added later.
              </span>
            </div>
            <div className="text-xs text-gray-500">
              Typical fields: username, display name, email, roles/groups.
            </div>
          </CardContent>
        </Card>
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
              const options = Array.from(e.target.selectedOptions, (o) => o.value);
              setNewRoles(options);
            }}
            className="border rounded p-1 min-w-[180px] h-[38px]"
          >
            {ROLE_CHOICES.map((r) => (
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
                      const options = Array.from(
                        e.target.selectedOptions,
                        (o) => o.value,
                      );
                      setEditRoles(options);
                    }}
                    className="border rounded p-1 min-w-[180px] h-[38px]"
                  >
                    {ROLE_CHOICES.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                ) : u.roles && u.roles.length ? (
                  u.roles
                    .map((rid) => {
                      const label = ROLE_CHOICES.find((r) => r.id === rid)?.label || rid;
                      const count = rolePermissionMap.get(rid)?.count ?? 0;
                      return `${label} (${count})`;
                    })
                    .join(", ")
                ) : (
                  <span className="text-gray-400">--</span>
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
        <strong>Tip:</strong> Each user can have one or more roles, which control
        their access throughout the system. Assign roles carefully. Use the
        Permissions page to define what each role can do.
      </div>
    </div>
  );
}
