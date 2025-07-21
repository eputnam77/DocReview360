import React, { useState } from "react";

interface CheckResult {
  [key: string]: unknown;
}

export default function CheckerPage() {
  const [result, setResult] = useState<CheckResult | null>(null);
  const [download, setDownload] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const res = await fetch("/api/tools/checker", {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      const data = await res.json();
      setResult(data.results);
      setDownload(`/downloads/${data.filename}`);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Document Checker</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="file"
          name="file"
          accept=".doc,.docx"
          className="border p-2"
          required
        />
        <button type="submit" className="px-3 py-2 bg-green-600 text-white">
          Check
        </button>
      </form>
      {result && (
        <pre className="whitespace-pre-wrap text-sm bg-gray-100 p-2">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
      {download && (
        <a href={download} className="text-blue-600 hover:underline">
          Download corrected document
        </a>
      )}
    </div>
  );
}
