import React from "react";

const DEFAULT_DOCS_URL = "https://eputnam77.github.io/DocReview360/";

export default function DocsPage() {
  const docsUrl = process.env.NEXT_PUBLIC_DOCS_URL ?? DEFAULT_DOCS_URL;

  return (
    <div className="w-full h-screen">
      <iframe
        src={docsUrl}
        title="Documentation"
        className="w-full h-full border-0"
      />
    </div>
  );
}
