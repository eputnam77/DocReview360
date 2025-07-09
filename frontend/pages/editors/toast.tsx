import React, { useRef } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";

// Toast UI Editor only works in browser, so use dynamic import with ssr: false
const Editor = dynamic(
  () => import("@toast-ui/react-editor").then((mod) => mod.Editor),
  { ssr: false },
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
    <div className="fixed inset-0 z-30 bg-white flex flex-col">
      <header className="flex items-center gap-2 bg-gray-100 px-6 py-3 border-b">
        <h1 className="text-xl font-bold mr-6">Toast Editor</h1>
        <span className="text-gray-500 text-sm">Markdown • WYSIWYG</span>
        <Button className="ml-auto" onClick={handleSave}>
          Save
        </Button>
      </header>
      <main className="flex-1 overflow-auto p-0">
        <Editor
          ref={editorRef}
          initialValue="Welcome to **Toast UI Editor**!\n\n- Edit in Markdown or WYSIWYG\n- This is fullscreen!"
          previewStyle="vertical"
          height="100%"
          initialEditType="markdown"
          useCommandShortcut={true}
          hideModeSwitch={false}
          theme="light"
          usageStatistics={false}
          className="w-full h-full"
        />
      </main>
    </div>
  );
}
