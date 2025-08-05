import { getDemoProject } from "@/data/demoProjects";
import { API } from "@/lib/api";
import { useRouter } from "next/router";
import React, { useEffect, useState } from "react";

const DOCUMENT_TYPES = [
  "Advisory Circular",
  "Policy Statement",
  "Release Notes",
];

export default function EditProjectPage() {
  const router = useRouter();
  const { id } = router.query;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [docId, setDocId] = useState("");
  const [title, setTitle] = useState("");
  const [sme, setSme] = useState("");
  const [docType, setDocType] = useState<string>("");
  const [description, setDescription] = useState("");

  // Fetch project details on mount
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    console.log('Edit page: Fetching project data from:', `${API}/projects/${id}`);

    fetch(`${API}/projects/${id}`)
      .then((r) => {
        console.log('Edit page: Response status:', r.status);
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}`);
        }
        return r.json();
      })
      .then((proj) => {
        console.log('Edit page: Received project data:', proj);
        // Map backend ProjectModel fields to frontend form fields
        setDocId(proj.id || "");
        setTitle(proj.name || "");
        setSme(proj.user || "");
        setDocType(proj.doc_type || "");
        setDescription(proj.name || ""); // Use name as description since backend doesn't have description
        setLoading(false);
      })
      .catch((error) => {
        console.error('Edit page: API call failed:', error);
        console.log('Edit page: Falling back to demo data');
        const demo = getDemoProject(String(id));
        if (demo) {
          setDocId(String(demo.number));
          setTitle(demo.title);
          setSme(demo.user || "");
          setDocType(demo.type);
          setDescription(demo.title);
        } else {
          setError("Could not load project.");
        }
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

    try {
      const res = await fetch(`${API}/projects/${id}`, {
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

  if (loading && !docId) return <div className="p-8">Loading…</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-xl mx-auto bg-white shadow-lg rounded-xl p-8">
        <h1 className="text-2xl font-bold mb-6">Edit Project</h1>
        <form
          className="space-y-5"
          onSubmit={handleSubmit}
          encType="multipart/form-data"
        >
          <div>
            <label htmlFor="docId" className="block text-sm font-medium mb-2">Document ID *</label>
            <input
              id="docId"
              type="text"
              value={docId}
              onChange={(e) => setDocId(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="title" className="block text-sm font-medium mb-2">Document Title *</label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="sme" className="block text-sm font-medium mb-2">Subject Matter Expert (SME)</label>
            <input
              id="sme"
              type="text"
              value={sme}
              onChange={(e) => setSme(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="docType" className="block text-sm font-medium mb-2">Document Type *</label>
            <select
              id="docType"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a document type</option>
              {DOCUMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="description" className="block text-sm font-medium mb-2">Description</label>
            <input
              id="description"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Saving..." : "Save Changes"}
          </button>
        </form>
      </div>
    </div>
  );
}
