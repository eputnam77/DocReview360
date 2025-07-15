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

interface Profile {
  picture: string;
  email: string;
  phone: string;
  shorthand: string;
  dashboards: string[];
}

const DASHBOARD_CHOICES = [
  { id: "main", label: "Main Dashboard" },
  { id: "user", label: "User Dashboard" },
  { id: "admin", label: "Admin Dashboard" },
];

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>({
    picture: "",
    email: "",
    phone: "",
    shorthand: "",
    dashboards: ["main"],
  });

  useEffect(() => {
    fetch("/api/profile")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setProfile(data);
      })
      .catch(() => {});
  }, []);

  const updateField = (key: keyof Profile, value: any) =>
    setProfile((p) => ({ ...p, [key]: value }));

  const toggleDashboard = (id: string, on: boolean) => {
    setProfile((p) => {
      const dashboards = on
        ? Array.from(new Set([...p.dashboards, id]))
        : p.dashboards.filter((d) => d !== id);
      return { ...p, dashboards };
    });
  };

  const handleSave = () => {
    fetch("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    }).catch(() => {});
    alert("Profile saved (demo)");
  };

  return (
    <div className="p-8 space-y-8 max-w-3xl">
      <h1 className="text-2xl font-bold">Profile Settings</h1>
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
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Default Dashboards</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {DASHBOARD_CHOICES.map((d) => (
            <label key={d.id} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={profile.dashboards.includes(d.id)}
                onChange={(e) => toggleDashboard(d.id, e.target.checked)}
              />
              <span>{d.label}</span>
            </label>
          ))}
        </CardContent>
      </Card>

      <Button variant="primary" size="lg" onClick={handleSave}>
        Save Changes
      </Button>
    </div>
  );
}
