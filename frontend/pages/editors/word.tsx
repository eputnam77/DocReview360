// frontend/pages/editors/word.tsx
import React from "react";

/**
 * Embeds a Word doc viewer using Microsoft's Office Online viewer.
 * To enable editing, the file must be on your own OneDrive/SharePoint and the user must have permission.
 */
export default function WordEditorPage() {
  // URL to a public .docx file (must be publicly accessible)
  const docUrl = encodeURIComponent("https://file-examples.com/wp-content/uploads/2017/02/file-sample_100kB.docx");

  // Use Office Online Viewer for public files
  const embedUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${docUrl}`;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow p-6">
        <h1 className="text-2xl font-bold mb-4">MS Word Online Viewer</h1>
        <iframe
          src={embedUrl}
          width="100%"
          height="600"
          frameBorder={0}
          style={{ border: "1px solid #ccc", borderRadius: "0.75rem", background: "#fff" }}
          allowFullScreen
          title="MS Word Document"
        ></iframe>
        <p className="text-sm text-gray-500 mt-3">
          This is a live view of a Word document using the free Microsoft Office Online Viewer.  
          To allow **editing**, see the instructions below.
        </p>
      </div>
    </div>
  );
}

