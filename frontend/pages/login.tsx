// app/login/page.tsx  (or pages/login.tsx)
"use client";

import React, { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";
import { toast } from "react-hot-toast";
import { useRouter } from "next/router";
import Link from "next/link";
import { API, setStoredAccessToken } from "@/lib/api";
import { useUserStore } from "@/state/user";
import { useTranslation } from "@/lib/useTranslation";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const refreshUser = useUserStore((state) => state.refresh);
  const { t } = useTranslation();

  async function handleLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`${API}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        credentials: "include",
        body: new URLSearchParams({
          username: username,
          password: password,
        }),
      });

      if (response.ok) {
        const tokenPayload = await response.json();
        const accessToken =
          typeof tokenPayload?.access_token === "string"
            ? tokenPayload.access_token.trim()
            : "";
        if (accessToken) {
          setStoredAccessToken(accessToken);
        }
        try {
          await refreshUser();
        } catch (error) {
          console.error("Failed to refresh user after login", error);
        }
        // Cookie is set by the server; simply redirect
        router.push("/projects");
        toast.success("Login successful");
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || "Login failed");
      }
    } catch (error) {
      toast.error("An error occurred during login");
      console.error("Login error:", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center
                    bg-gradient-to-b from-gray-50 to-gray-100
                    dark:from-gray-950 dark:to-gray-900">
      <Card className="w-full max-w-md mx-4 shadow-2xl">
        <CardHeader className="space-y-1 text-center">
          <LogIn className="mx-auto h-10 w-10 text-indigo-600" />
          <CardTitle className="text-2xl font-bold">
            {t("login.title")}
          </CardTitle>
          <CardDescription>
            Welcome back! Enter your credentials.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form className="space-y-4" onSubmit={handleLogin} autoComplete="on">
            <div className="space-y-2">
              <Label htmlFor="username">{t("login.username")}</Label>
              <Input
                id="username"
                type="text"
                name="username"
                placeholder="alice or bob"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t("login.password")}</Label>
              <Input
                id="password"
                type="password"
                name="password"
                placeholder="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <Button type="submit" className="w-full mt-2" disabled={loading}>
              {loading ? t("login.loading") : t("login.submit")}
            </Button>

            <div className="text-center text-sm text-gray-500 dark:text-gray-400 mt-4">
              <p>Test accounts:</p>
              <p className="font-mono">alice/password (admin)</p>
              <p className="font-mono">bob/password (auditor)</p>
            </div>

            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              Don't have an account?{" "}
              <Link href="/signup" className="underline">
                Sign up
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
