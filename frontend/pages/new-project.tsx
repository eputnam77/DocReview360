// pages/new-project.tsx or app/new-project/page.tsx
"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

// Dummy data, replace with your real list of SMEs and doc types
const SME_LIST = [
  { id: "alice", name: "Alice Smith" },
  { id: "bob", name: "Bob Johnson" },
  { id: "carol", name: "Carol Lee" },
];
const DOC_TYPES = [
  "Memo",
  "Report",
  "Order",
  "Policy",
  "Manual",
  "Other",
];

export default function NewProject() {
  const [docId, setDocId] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [sme, setSme] = useState<string | undefined>();
  const [docType, setDocType] = useState<string | undefined>();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // 1. Upload file (if any)
      let uploadedFileUrl: string | undefined;
      if (file) {
        // For demo: replace with your upload logic (S3, API, etc.)
        // e.g. await uploadFile(file)
        uploadedFileUrl = file.name; // placeholder
      }

      // 2. Create project in your backend
      const resp = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          documentId: docId,
          title: docTitle,
          sme,
          documentType: docType,
          fileUrl: uploadedFileUrl,
        }),
      });

      if (!resp.ok) throw new Error("Failed to create project");
      router.push("/projects");
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-50 to-white">
      <Card className="w-full max-w-lg shadow-xl">
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Create New Project</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={submit} autoComplete="off">
            <div className="space-y-2">
              <Label htmlFor="doc-id">Document ID</Label>
              <Input
                id="doc-id"
                type="text"
                value={docId}
                onChange={e => setDocId(e.target.value)}
                placeholder="Unique document ID"
                required
                minLength={2}
                maxLength={32}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="doc-title">Document Title</Label>
              <Input
                id="doc-title"
                type="text"
                value={docTitle}
                onChange={e => setDocTitle(e.target.value)}
                placeholder="Document title"
                required
                minLength={2}
                maxLength={128}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="doc-type">Document Type</Label>
              <Select value={docType} onValueChange={setDocType} required>
                <SelectTrigger id="doc-type">
                  <SelectValue placeholder="Choose type…" />
                </SelectTrigger>
                <SelectContent>
                  {DOC_TYPES.map(type => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="sme">Subject Matter Expert (SME)</Label>
              <Select value={sme} onValueChange={setSme} required>
                <SelectTrigger id="sme">
                  <SelectValue placeholder="Choose SME…" />
                </SelectTrigger>
                <SelectContent>
                  {SME_LIST.map(user => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="upload">Upload Word Document</Label>
              <Input
                id="upload"
                ref={fileInputRef}
                type="file"
                accept=".doc,.docx"
                onChange={e => setFile(e.target.files?.[0] || null)}
              />
              {file && (
                <p className="text-xs text-gray-600">
                  Selected: <span className="font-semibold">{file.name}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="ml-2 text-xs"
                    onClick={() => {
                      setFile(null);
                      fileInputRef.current?.value && (fileInputRef.current.value = "");
                    }}
                  >
                    Remove
                  </Button>
                </p>
              )}
            </div>
            {error && (
              <div className="text-red-600 text-sm">{error}</div>
            )}
            <Button
              type="submit"
              className="w-full"
              disabled={loading || !docId || !docTitle || !docType || !sme}
            >
              {loading ? "Creating..." : "Create Project"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center text-xs text-gray-400">
          A project ID will be generated automatically.
        </CardFooter>
      </Card>
    </main>
  );
}
