import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import UploadDropzone from "@/components/workflow/UploadDropzone";

const DOCUMENT_TYPES = [
  "Advisory Circular",
  "Order",
  "Policy",
  "Memo",
  "Report",
  "Other",
];

export default function EditProjectPage() {
  const router = useRouter();
  const { id } = router.query;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [docId, setDocId] = useState("");
  const [title, setTitle] = useState("");
  const [sme, setSme] = useState("");
  const [docType, setDocType] = useState<string | undefined>(undefined);
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);

  // Fetch project details on mount
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`/api/projects/${id}`)
      .then((r) => r.json())
      .then((proj) => {
        setDocId(proj.docId || "");
        setTitle(proj.title || "");
        setSme(proj.sme || "");
        setDocType(proj.docType || "");
        setDescription(proj.description || "");
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load project.");
        setLoading(false);
      });
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!docId.trim() || !title.trim() || !docType) {
      setError("Please fill all required fields.");
      return;
    }
    setLoading(true);

    const formData = new FormData();
    formData.append("docId", docId);
    formData.append("title", title);
    formData.append("sme", sme);
    formData.append("docType", docType);
    formData.append("description", description);
    if (file) formData.append("file", file);

    try {
      const res = await fetch(`/api/projects/${id}`, {
        method: "PUT",
        body: formData,
      });
      if (!res.ok) throw new Error("Failed to update project");
      router.push(`/projects/${id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8">Loading…</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-xl mx-auto bg-white shadow-lg rounded-xl p-8">
        <h1 className="text-2xl font-bold mb-6">Edit Project</h1>
        <form className="space-y-5" onSubmit={handleSubmit} encType="multipart/form-data">
          <div>
            <Label htmlFor="docId">Document ID *</Label>
            <Input
              id="docId"
              value={docId}
              onChange={e => setDocId(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="title">Document Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={e => setTitle(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="sme">Subject Matter Expert (SME)</Label>
            <Input
              id="sme"
              value={sme}
              onChange={e => setSme(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="docType">Document Type *</Label>
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger id="docType">
                <SelectValue placeholder="Select a document type" />
              </SelectTrigger>
              <SelectContent>
                {DOCUMENT_TYPES.map(type => (
                  <SelectItem key={type} value={type}>{type}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>
          <div>
            <Label>Replace Document File (.docx, .pdf, .txt)</Label>
            <UploadDropzone
              value={file}
              onChange={setFile}
              accept=".docx,.pdf,.txt"
              maxSizeMB={20}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button
            type="submit"
            disabled={loading}
            className="w-full"
          >
            {loading ? "Saving..." : "Save Changes"}
          </Button>
        </form>
      </div>
    </div>
  );
}

