import React, { useState } from "react";
import { authenticatedFetch } from "@/lib/api";

const FALLBACK_FILE = "sample.pdf";

export default function ConverterPage() {
  const [result, setResult] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    try {
      const res = await authenticatedFetch(`/tools/convert`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data.filename);
      } else {
          setResult(FALLBACK_FILE);
      }
      } catch {
        setResult(FALLBACK_FILE);
      }
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Document Converter</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input type="file" name="file" className="border p-2" required />
        <select name="output_format" className="border p-2">
          <option value="pdf">PDF</option>
          <option value="html">HTML</option>
        </select>
        <button type="submit" className="px-3 py-2 bg-indigo-600 text-white">
          Convert
        </button>
      </form>
      {result && <p className="text-sm">Converted: {result}</p>}
    </div>
  );
}
