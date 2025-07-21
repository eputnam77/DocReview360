import React from "react";
import Link from "next/link";

export default function ToolsPage() {
  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Tools</h1>
      <ul className="list-disc pl-5 space-y-2">
        <li>
          <Link href="/tools/converter" className="text-indigo-700 underline">
            Document Converter
          </Link>
        </li>
        <li>
          <Link href="/tools/checker" className="text-indigo-700 underline">
            Document Checker
          </Link>
        </li>
      </ul>
    </div>
  );
}
