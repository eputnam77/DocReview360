import React from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

export default function TiptapEditorPage() {
  const editor = useEditor({
    extensions: [StarterKit],
    content: "<p>Welcome to <b>TipTap</b>!</p>",
    autofocus: true,
  });

  const handleSave = () => {
    if (editor) {
      alert(editor.getHTML());
      // You can POST editor.getHTML() or editor.getJSON() to your backend.
    }
  };

  if (!editor) return <div>Loading TipTap...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow p-6">
        <h1 className="text-2xl font-bold mb-4">TipTap Editor</h1>
        {/* Toolbar */}
        <div className="flex gap-2 mb-2">
          <button
            type="button"
            className={`px-2 py-1 rounded ${editor.isActive('bold') ? 'bg-indigo-100' : ''}`}
            onClick={() => editor.chain().focus().toggleBold().run()}
            aria-label="Bold"
          >
            <b>B</b>
          </button>
          <button
            type="button"
            className={`px-2 py-1 rounded ${editor.isActive('italic') ? 'bg-indigo-100' : ''}`}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            aria-label="Italic"
          >
            <i>I</i>
          </button>
          <button
            type="button"
            className={`px-2 py-1 rounded ${editor.isActive('bulletList') ? 'bg-indigo-100' : ''}`}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            aria-label="Bullet List"
          >
            • List
          </button>
          <button
            type="button"
            className={`px-2 py-1 rounded ${editor.isActive('orderedList') ? 'bg-indigo-100' : ''}`}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            aria-label="Ordered List"
          >
            1. List
          </button>
          <button
            type="button"
            className="px-2 py-1 rounded"
            onClick={() => editor.chain().focus().undo().run()}
            aria-label="Undo"
            disabled={!editor.can().undo()}
          >
            Undo
          </button>
          <button
            type="button"
            className="px-2 py-1 rounded"
            onClick={() => editor.chain().focus().redo().run()}
            aria-label="Redo"
            disabled={!editor.can().redo()}
          >
            Redo
          </button>
        </div>
        {/* Editor */}
        <EditorContent
          editor={editor}
          className="border rounded min-h-[300px] p-4 bg-gray-50 mb-4"
        />
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Save
        </button>
      </div>
    </div>
  );
}
