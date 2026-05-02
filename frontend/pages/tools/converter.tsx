import React, { useState } from "react";
import { authenticatedFetch } from "@/lib/api";

const FALLBACK_FILE = "sample.pdf";

export function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) {
    return null;
  }
  const match = header.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
  return match ? decodeURIComponent(match[1]) : null;
}

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
        const filename =
          filenameFromContentDisposition(res.headers.get("content-disposition")) ??
          FALLBACK_FILE;
        const blob = await res.blob();
        if (typeof window !== "undefined") {
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = filename;
          link.click();
          window.URL.revokeObjectURL(url);
        }
        setResult(filename);
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
          <option value="markdown">Markdown (.md)</option>
          <option value="txt">Plain Text (.txt)</option>
          <option value="docx">Word Document (.docx)</option>
          <option value="confluence">Confluence Wiki</option>
        </select>
        <button type="submit" className="px-3 py-2 bg-indigo-600 text-white">
          Convert
        </button>
      </form>
      {result && <p className="text-sm">Converted: {result}</p>}
    </div>
  );
}
