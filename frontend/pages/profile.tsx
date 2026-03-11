import React, { useEffect, useMemo, useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Input,
  FileInput,
  Label,
} from "@/components";
import { Avatar } from "@/components/ui/avatar";
import { authenticatedFetch } from "@/lib/api";
import { toast } from "react-hot-toast";
import { useUserStore } from "@/state/user";

// --- Types ---
interface Profile {
  picture: string;
  displayName: string;
  email: string;
  phone: string;
  shorthand: string;
  jobTitle: string;
  department: string;
  timeZone: string;
  dashboards?: string[];
  permissions?: string[];
  roles?: string[];
  notificationEmail: boolean;
  notificationSMS: boolean;
  twoFA: boolean;
  theme: "system" | "light" | "dark";
}

interface RolePermissionSummary {
  role: string;
  permissions: string[];
  count: number;
  default_permissions: string[];
  default_count: number;
  is_default: boolean;
}

const DASHBOARD_CHOICES = [
  { id: "main", label: "Main Dashboard" },
  { id: "user", label: "User Dashboard" },
  { id: "admin", label: "Admin Dashboard" },
];

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

const TIME_ZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "Australia/Sydney",
];

const EMPTY_PROFILE: Profile = {
  picture: "",
  displayName: "",
  email: "",
  phone: "",
  shorthand: "",
  jobTitle: "",
  department: "",
  timeZone: "America/New_York",
  dashboards: ["main"],
  permissions: ["user"],
  roles: [],
  notificationEmail: true,
  notificationSMS: false,
  twoFA: false,
  theme: "system",
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>({ ...EMPTY_PROFILE });
  const [password, setPassword] = useState("");
  const setTheme = useUserStore((s) => s.setTheme);
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [pictureFile, setPictureFile] = useState<File | null>(null);
  const [rolePermissions, setRolePermissions] = useState<RolePermissionSummary[]>([]);

  useEffect(() => {
    authenticatedFetch('/profile')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          const themeValue = ["system", "light", "dark"].includes(data.preferences?.theme)
            ? data.preferences.theme
            : ["system", "light", "dark"].includes(data.theme)
              ? data.theme
              : "system";
          setProfile({
            ...EMPTY_PROFILE,
            ...data,
            dashboards: Array.isArray(data.dashboards) ? data.dashboards : ["main"],
            permissions: Array.isArray(data.permissions) ? data.permissions : ["user"],
            roles: Array.isArray(data.roles) ? data.roles : [],
            theme: themeValue,
          });
          setTheme(themeValue);
        } else {
          setProfile(EMPTY_PROFILE);
        }
      })
      .catch(() => setProfile(EMPTY_PROFILE));
  }, [setTheme]);

  useEffect(() => {
    authenticatedFetch('/rbac/role-permissions')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (Array.isArray(data)) {
          setRolePermissions(data);
        } else {
          setRolePermissions([]);
        }
      })
      .catch(() => setRolePermissions([]));
  }, []);

  const updateField = (key: keyof Profile, value: any) =>
    setProfile((p) => ({ ...p, [key]: value }));

  const handlePictureFile = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = e.target.files?.[0] || null;
    setPictureFile(file);
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) =>
        updateField("picture", ev.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  const handleSave = async () => {
    if (password && password !== passwordConfirm) {
      toast.error("Passwords do not match");
      return;
    }
    const resp = await authenticatedFetch('/profile', {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...profile,
        preferences: {
          theme: profile.theme,
        },
        password: password || undefined,
      }),
    }).catch(() => null);

    if (!resp || !resp.ok) {
      toast.error("Failed to save profile");
      return;
    }

    setTheme(profile.theme);
    toast.success("Profile saved");
    setPassword("");
    setPasswordConfirm("");
    setPictureFile(null);
  };

  const userDashboards = Array.isArray(profile.dashboards) ? profile.dashboards : [];
  const userRoles = Array.isArray(profile.roles) ? profile.roles : [];

  const roleLabel = useMemo(() => {
    const mapping = new Map<string, string>();
    ROLE_CHOICES.forEach((role) => mapping.set(role.id, role.label));
    return mapping;
  }, []);

  const rolePermissionMap = useMemo(() => {
    const mapping = new Map<string, RolePermissionSummary>();
    rolePermissions.forEach((role) => mapping.set(role.role, role));
    return mapping;
  }, [rolePermissions]);

  const effectivePermissions = useMemo(() => {
    const permissions = new Set<string>();
    userRoles.forEach((role) => {
      const summary = rolePermissionMap.get(role);
      summary?.permissions.forEach((perm) => permissions.add(perm));
    });
    return Array.from(permissions).sort();
  }, [rolePermissionMap, userRoles]);

  return (
    <div className="p-8 space-y-8 max-w-3xl">
      <h1 className="text-2xl font-bold mb-2">Profile Settings</h1>
      <p className="text-gray-600 text-sm mb-4">
        Update your personal details, preferences, and security settings.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <Avatar src={profile.picture} alt="Profile picture" size={64} />
            <div className="flex-1">
              <Label className="block mb-1">Profile Picture URL</Label>
              <Input
                placeholder="https://example.com/me.jpg"
                value={profile.picture}
                onChange={(e) => updateField("picture", e.target.value)}
              />
              <div className="text-xs text-gray-500 mt-1">
                Paste a link to your photo or upload an image below.
              </div>
              <Label className="block mb-1 mt-3">Or Upload Picture</Label>
              <FileInput accept="image/*" onChange={handlePictureFile} />
              <div className="text-xs text-gray-500 mt-1">
                JPG, PNG or GIF up to a few MB.
              </div>
            </div>
          </div>
          <div>
            <Label>Display Name</Label>
            <Input
              placeholder="Full Name"
              value={profile.displayName}
              onChange={(e) => updateField("displayName", e.target.value)}
            />
            <div className="text-xs text-gray-500 mt-1">
              How your name will appear to others.
            </div>
          </div>
          <div>
            <Label>Email</Label>
            <Input
              type="email"
              value={profile.email}
              onChange={(e) => updateField("email", e.target.value)}
            />
          </div>
          <div>
            <Label>Phone</Label>
            <Input
              value={profile.phone}
              onChange={(e) => updateField("phone", e.target.value)}
            />
          </div>
          <div>
            <Label>Shorthand</Label>
            <Input
              placeholder="e.g. JD"
              value={profile.shorthand}
              onChange={(e) => updateField("shorthand", e.target.value)}
            />
            <div className="text-xs text-gray-500 mt-1">
              Initials or short handle for signatures/comments.
            </div>
          </div>
          <div>
            <Label>Job Title</Label>
            <Input
              placeholder="e.g. Project Analyst"
              value={profile.jobTitle}
              onChange={(e) => updateField("jobTitle", e.target.value)}
            />
          </div>
          <div>
            <Label>Department</Label>
            <Input
              placeholder="e.g. Regulatory Affairs"
              value={profile.department}
              onChange={(e) => updateField("department", e.target.value)}
            />
          </div>
          <div>
            <Label>Time Zone</Label>
            <select
              className="w-full border rounded p-2 mt-1"
              value={profile.timeZone}
              onChange={(e) => updateField("timeZone", e.target.value)}
            >
              <option value="">Select time zone</option>
              {TIME_ZONES.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <CardContent>
          <Label>Theme</Label>
          <select
            className="w-full border rounded p-2 mt-1"
            value={profile.theme}
            onChange={(e) => {
              const nextTheme = e.target.value as Profile["theme"];
              updateField("theme", nextTheme);
              setTheme(nextTheme);
            }}
          >
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Default Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-2 text-gray-600 text-sm">
            Your current default dashboard:
          </div>
          <div className="bg-gray-50 border rounded px-4 py-2 mb-2 font-semibold">
            {userDashboards.length === 0
              ? <span className="text-gray-400">No dashboard set</span>
              : DASHBOARD_CHOICES.filter(d => userDashboards.includes(d.id))
                  .map(d => d.label).join(", ")
            }
          </div>
          <div className="text-xs text-gray-500 mb-1">
            Contact your administrator to change your dashboard access.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>System Permissions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <div className="mb-2 text-gray-600 text-sm">
              Your current system role(s):
            </div>
            <div className="bg-gray-50 border rounded px-4 py-2 font-semibold">
              {userRoles.length === 0
                ? <span className="text-gray-400">No role assigned</span>
                : userRoles
                    .map((role) => {
                      const summary = rolePermissionMap.get(role);
                      const count = summary?.count ?? 0;
                      return `${roleLabel.get(role) || role} (${count})`;
                    })
                    .join(", ")
              }
            </div>
          </div>
          <div>
            <div className="mb-2 text-gray-600 text-sm">
              Effective permissions ({effectivePermissions.length}):
            </div>
            <div className="text-xs text-gray-500">
              {effectivePermissions.length
                ? <span className="font-mono">{effectivePermissions.join(", ")}</span>
                : <span className="text-gray-400">No permissions available</span>
              }
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Permission counts are based on role defaults or configured overrides.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Security</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Change Password</Label>
            <Input
              type="password"
              placeholder="New password"
              value={password}
              autoComplete="new-password"
              onChange={e => setPassword(e.target.value)}
            />
            <Input
              type="password"
              placeholder="Confirm new password"
              value={passwordConfirm}
              autoComplete="new-password"
              onChange={e => setPasswordConfirm(e.target.value)}
              className="mt-2"
            />
            <div className="text-xs text-gray-500 mt-1">
              Leave blank if you do not want to change your password.
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Label>Two-Factor Authentication</Label>
            <span className={profile.twoFA ? "text-green-600 font-semibold" : "text-red-500 font-semibold"}>
              {profile.twoFA ? "Enabled" : "Disabled"}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-3">
            <input
              type="checkbox"
              checked={profile.notificationEmail}
              onChange={e => updateField("notificationEmail", e.target.checked)}
              id="notify-email"
              className="mr-2"
            />
            <Label htmlFor="notify-email" className="font-normal">
              Email me about project updates and reviews
            </Label>
          </div>
          <div className="flex items-center gap-4">
            <input
              type="checkbox"
              checked={profile.notificationSMS}
              onChange={e => updateField("notificationSMS", e.target.checked)}
              id="notify-sms"
              className="mr-2"
            />
            <Label htmlFor="notify-sms" className="font-normal">
              Text me about urgent updates
            </Label>
          </div>
        </CardContent>
      </Card>

      <Button variant="primary" size="lg" onClick={handleSave}>
        Save Changes
      </Button>
    </div>
  );
}
