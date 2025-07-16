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

// --- Define roles and actions ---
const ROLE_CHOICES = [
  { id: "admin", label: "Administrator" },
  { id: "pm", label: "Program/Project Manager" },
  { id: "user", label: "User (Contributor)" },
  { id: "reviewer", label: "Reviewer" },
  { id: "editor", label: "Editor" },
  { id: "viewer", label: "Viewer (Read-only)" },
];

const ACTION_CHOICES = [
  { id: "create_project", label: "Create Project" },
  { id: "delete_project", label: "Delete Project" },
  { id: "manage_users", label: "Manage Users" },
  { id: "assign_roles", label: "Assign Roles" },
  { id: "add_document", label: "Add Document" },
  { id: "edit_document", label: "Edit Document" },
  { id: "delete_document", label: "Delete Document" },
  { id: "view_document", label: "View Document" },
  { id: "comment_document", label: "Comment on Document" },
  { id: "review_document", label: "Review Document" },
  { id: "approve_document", label: "Approve Document" },
  { id: "reject_document", label: "Reject Document" },
  { id: "manage_workflows", label: "Manage Workflows" },
  { id: "view_audit_log", label: "View Audit Log" },
];

interface Permission {
  id: string;
  role: string;
  action: string;
  allowed: boolean;
}

// --- Example permissions for initial view ---
const DEMO_PERMISSIONS: Permission[] = [
  { id: "admin-delete_project", role: "admin", action: "delete_project", allowed: true },
  { id: "pm-delete_project", role: "pm", action: "delete_project", allowed: false },
  { id: "user-view_document", role: "user", action: "view_document", allowed: true },
  { id: "reviewer-approve_document", role: "reviewer", action: "approve_document", allowed: true },
  { id: "viewer-edit_document", role: "viewer", action: "edit_document", allowed: false },
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
      <h1 className="text-2xl font-bold mb-1">Permissions Management</h1>
      <div className="text-gray-600 text-sm mb-4">
        Define which roles are allowed to perform which actions in the system. For example, only administrators may delete projects, but all users may view documents.
      </div>
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          addPermission();
        }}
      >
        <div>
          <label className="block text-xs font-semibold mb-1">Role</label>
          <select
            className="border rounded p-1"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
          >
            <option value="">Choose role…</option>
            {ROLE_CHOICES.map((r) => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold mb-1">Action</label>
          <select
            className="border rounded p-1"
            value={newAction}
            onChange={(e) => setNewAction(e.target.value)}
          >
            <option value="">Choose action…</option>
            {ACTION_CHOICES.map((a) => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-1 text-sm ml-2">
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
              <TableCell className="font-mono">
                {ROLE_CHOICES.find(r => r.id === p.role)?.label || p.role}
              </TableCell>
              <TableCell>
                {ACTION_CHOICES.find(a => a.id === p.action)?.label || p.action}
              </TableCell>
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
      <div className="mt-6 text-xs text-gray-500 max-w-2xl">
        <strong>Tip:</strong> Roles and actions above are examples and can be tailored to your organization. 
        <ul className="list-disc pl-5 mt-1">
          <li>Administrators manage all settings, users, and data.</li>
          <li>Program/Project Managers handle project lifecycle and workflows.</li>
          <li>Reviewers and editors participate in document reviews and edits.</li>
          <li>General users and viewers have limited, controlled access.</li>
        </ul>
      </div>
    </div>
  );
}
