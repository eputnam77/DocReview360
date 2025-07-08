// app/login/page.tsx (or pages/login.tsx)
"use client";

import React from "react";
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

export default function LoginPage() {
  // Replace this stub with your real login logic
  function handleLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    // e.currentTarget.email.value and e.currentTarget.password.value
    // Add real auth logic here
    alert("Login submitted (demo)");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-600 dark:from-indigo-900 dark:via-purple-900 dark:to-pink-900">
      <Card className="w-full max-w-md mx-4 shadow-2xl">
        <CardHeader className="space-y-1 text-center">
          <LogIn className="mx-auto h-10 w-10 text-indigo-600" />
          <CardTitle className="text-2xl font-bold">Sign in to DocuFlow</CardTitle>
          <CardDescription>Welcome back! Enter your credentials.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleLogin} autoComplete="on">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                name="email"
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                name="password"
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
            </div>
            <Button type="submit" className="w-full mt-2">
              Continue
            </Button>
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              Don’t have an account?{" "}
              <a href="/sign-up" className="underline">
                Sign up
              </a>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
