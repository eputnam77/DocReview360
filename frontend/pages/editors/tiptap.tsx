import React from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

export default function TiptapPage() {
  const editor = useEditor({
    extensions: [StarterKit],
    content: "<p>Start writing...</p>",
  });

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Tiptap Editor</h1>
      {editor && (
        <EditorContent
          editor={editor}
          className="min-h-[300px] border rounded-md p-4 bg-white"
        />
      )}
    </div>
  );
}
