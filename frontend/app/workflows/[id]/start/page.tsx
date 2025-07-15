// frontend/app/workflows/[id]/start/page.tsx

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UploadDropzone } from "@/components/workflow";

type Props = { params: { id: string } };

export default function StartWorkflowPage({ params }: Props) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (f: File | null) => setFile(f);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("title", title);
      if (file) {
        formData.append("file", file);
      }
      const resp = await fetch(`/api/workflows/${params.id}/start`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        throw new Error("request failed");
      }
      setTitle("");
      setFile(null);
    } catch (err: any) {
      setError("Failed to start workflow");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
      <form
        id={`start-${params.id}`}
        className="w-full max-w-md space-y-6 rounded-xl bg-white dark:bg-gray-900 shadow-lg p-8"
        onSubmit={handleSubmit}
        autoComplete="off"
      >
        <h1 className="text-2xl font-bold mb-2">Start Workflow</h1>
        <div className="space-y-2">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter document title"
            required
          />
        </div>
        <div className="space-y-2">
          <Label>Attach a file (Word)</Label>
          <UploadDropzone
            onDrop={(files) => handleFileChange(files[0] || null)}
            accept=".doc,.docx"
          />
          {file && (
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Selected: <span className="font-semibold">{file.name}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="ml-2"
                onClick={() => setFile(null)}
              >
                Remove
              </Button>
            </div>
          )}
        </div>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        <Button type="submit" className="w-full" disabled={loading || !title}>
          {loading ? "Starting..." : "Start Workflow"}
        </Button>
      </form>
    </main>
  );
}
