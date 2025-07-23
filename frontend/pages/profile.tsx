import React, { useEffect, useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Input,
  Label,
} from "@/components";
import { Avatar } from "@/components/ui/avatar";
import { API } from "@/lib/api";

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
  notificationEmail: boolean;
  notificationSMS: boolean;
  twoFA: boolean;
  theme: "system" | "light" | "dark";
}

const DASHBOARD_CHOICES = [
  { id: "main", label: "Main Dashboard" },
  { id: "user", label: "User Dashboard" },
  { id: "admin", label: "Admin Dashboard" },
];

const PERMISSION_CHOICES = [
  { id: "user", label: "Standard User" },
  { id: "editor", label: "Editor" },
  { id: "admin", label: "Administrator" },
  { id: "reviewer", label: "Reviewer" },
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

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>({
    picture: "",
    displayName: "",
    email: "",
    phone: "",
    shorthand: "",
    jobTitle: "",
    department: "",
    timeZone: "",
    dashboards: ["main"],
    permissions: ["user"],
    notificationEmail: true,
    notificationSMS: false,
    twoFA: false,
    theme: "system",
  });
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  useEffect(() => {
    fetch(`${API}/profile`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setProfile({
          ...profile,
          ...data,
          dashboards: Array.isArray(data.dashboards) ? data.dashboards : ["main"],
          permissions: Array.isArray(data.permissions) ? data.permissions : ["user"],
          theme: ["system", "light", "dark"].includes(data.theme) ? data.theme : "system",
        });
      })
      .catch(() => {});
    // eslint-disable-next-line
  }, []);

  const updateField = (key: keyof Profile, value: any) =>
    setProfile((p) => ({ ...p, [key]: value }));

  const handleSave = () => {
    if (password && password !== passwordConfirm) {
      alert("Passwords do not match!");
      return;
    }
    fetch(`${API}/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...profile, password: password || undefined }),
    }).catch(() => {});
    alert("Profile saved (demo)");
    setPassword("");
    setPasswordConfirm("");
  };

  // Safeguard for undefined permissions/dashboards
  const userDashboards = Array.isArray(profile.dashboards) ? profile.dashboards : [];
  const userPermissions = Array.isArray(profile.permissions) ? profile.permissions : [];

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
                Paste a link to your photo, or leave blank for initials.
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
            onChange={(e) => updateField("theme", e.target.value as Profile["theme"])}
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
        <CardContent>
          <div className="mb-2 text-gray-600 text-sm">
            Your current system role(s):
          </div>
          <div className="bg-gray-50 border rounded px-4 py-2 mb-2 font-semibold">
            {userPermissions.length === 0
              ? <span className="text-gray-400">No role assigned</span>
              : PERMISSION_CHOICES.filter(p => userPermissions.includes(p.id))
                  .map(p => p.label).join(", ")
            }
          </div>
          <div className="text-xs text-gray-500 mb-1">
            Roles control your access and abilities in the system.
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
            {/* Optional: 2FA enable/disable buttons */}
            {/* <Button size="sm" onClick={() => updateField("twoFA", !profile.twoFA)}>
              {profile.twoFA ? "Disable" : "Enable"}
            </Button> */}
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
