import React, { useEffect, useMemo, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { API, authenticatedFetch } from "@/lib/api";
import { toast } from "react-hot-toast";

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

interface RolePermissionSummary {
  role: string;
  permissions: string[];
  count: number;
  default_permissions: string[];
  default_count: number;
  is_default: boolean;
}

export default function PermissionsPage() {
  const [roles, setRoles] = useState<RolePermissionSummary[]>([]);
  const [inputs, setInputs] = useState<Record<string, string>>({});

  const roleLabel = useMemo(() => {
    const mapping = new Map<string, string>();
    ROLE_CHOICES.forEach((role) => mapping.set(role.id, role.label));
    return mapping;
  }, []);

  const loadRoles = async () => {
    try {
      const resp = await authenticatedFetch(`${API}/rbac/role-permissions`);
      const data = resp.ok ? await resp.json() : [];
      setRoles(Array.isArray(data) ? data : []);
    } catch {
      setRoles([]);
    }
  };

  useEffect(() => {
    void loadRoles();
  }, []);

  const updateRole = async (role: string, permissions: string[]) => {
    const resp = await authenticatedFetch(
      `${API}/rbac/role-permissions/${encodeURIComponent(role)}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ permissions }),
      },
    );
    if (!resp.ok) {
      toast.error("Failed to update permissions");
      return;
    }
    const updated = (await resp.json()) as RolePermissionSummary;
    setRoles((prev) => prev.map((item) => (item.role === role ? updated : item)));
    toast.success("Permissions updated");
  };

  const resetRole = async (role: string) => {
    const resp = await authenticatedFetch(
      `${API}/rbac/role-permissions/${encodeURIComponent(role)}`,
      {
        method: "DELETE",
      },
    );
    if (!resp.ok) {
      toast.error("Failed to reset permissions");
      return;
    }
    const updated = (await resp.json()) as RolePermissionSummary;
    setRoles((prev) => prev.map((item) => (item.role === role ? updated : item)));
    toast.success("Permissions reset to default");
  };

  const addPermission = (role: RolePermissionSummary) => {
    const value = (inputs[role.role] || "").trim().toLowerCase();
    if (!value) return;
    const next = Array.from(new Set([...(role.permissions || []), value])).sort();
    void updateRole(role.role, next);
    setInputs((prev) => ({ ...prev, [role.role]: "" }));
  };

  const removePermission = (role: RolePermissionSummary, perm: string) => {
    const next = (role.permissions || []).filter((p) => p !== perm);
    void updateRole(role.role, next);
  };

  return (
    <div className="p-8 space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold mb-1">Permissions Management</h1>
        <div className="text-gray-600 text-sm">
          Edit role permissions and compare them to system defaults. Updates are
          persisted immediately.
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {roles.map((role) => (
          <Card key={role.role} className="h-full">
            <CardHeader className="space-y-1">
              <CardTitle className="text-base">
                {roleLabel.get(role.role) || role.role}
              </CardTitle>
              <div className="text-xs text-gray-500">
                {role.count} permission{role.count === 1 ? "" : "s"} - default {role.default_count}
                {role.is_default ? " (default)" : " (customized)"}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {role.permissions.length ? (
                  role.permissions.map((perm) => (
                    <span
                      key={`${role.role}-${perm}`}
                      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs"
                    >
                      <span className="font-mono">{perm}</span>
                      <button
                        type="button"
                        className="text-red-600"
                        onClick={() => removePermission(role, perm)}
                        aria-label={`Remove ${perm}`}
                      >
                        x
                      </button>
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-400">No permissions configured.</span>
                )}
              </div>

              <div className="flex flex-wrap gap-2 items-center">
                <Input
                  placeholder="Add permission"
                  value={inputs[role.role] || ""}
                  onChange={(e) =>
                    setInputs((prev) => ({ ...prev, [role.role]: e.target.value }))
                  }
                  className="max-w-xs"
                />
                <Button size="sm" onClick={() => addPermission(role)}>
                  Add
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => resetRole(role.role)}
                >
                  Reset to default
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Table caption="Role Permissions Summary">
        <TableHeader>
          <TableRow>
            <TableHead>Role</TableHead>
            <TableHead>Current</TableHead>
            <TableHead>Default</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {roles.map((role) => (
            <TableRow key={`row-${role.role}`}>
              <TableCell className="font-semibold">
                {roleLabel.get(role.role) || role.role}
              </TableCell>
              <TableCell>{role.count}</TableCell>
              <TableCell>{role.default_count}</TableCell>
              <TableCell>{role.is_default ? "Default" : "Customized"}</TableCell>
            </TableRow>
          ))}
          {roles.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-gray-400 py-6">
                No role permissions available.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
