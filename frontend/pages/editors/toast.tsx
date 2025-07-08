import React, { useRef } from "react";
import dynamic from "next/dynamic";

// Toast Editor only works in browser, so use dynamic import with ssr: false
const Editor = dynamic(
  () => import("@toast-ui/react-editor").then((mod) => mod.Editor),
  { ssr: false }
);

import "@toast-ui/editor/dist/toastui-editor.css";

export default function ToastEditorPage() {
  const editorRef = useRef<any>(null);

  const handleSave = () => {
    if (editorRef.current) {
      const markdown = editorRef.current.getInstance().getMarkdown();
      alert("Markdown content:\n\n" + markdown);
      // You can also use getHTML() for HTML output
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Toast Editor</h1>
        <Editor
          ref={editorRef}
          initialValue="Welcome to **Toast UI Editor**!"
          previewStyle="vertical"
          height="400px"
          initialEditType="markdown"
          useCommandShortcut={true}
        />
        <button
          onClick={handleSave}
          className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Save
        </button>
      </div>
    </div>
  );
}

