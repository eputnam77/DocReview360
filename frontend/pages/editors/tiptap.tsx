import React from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import { Bold, Italic, Strikethrough, Underline as UnderlineIcon, Code, List, ListOrdered, Blockquote, Undo2, Redo2, Heading } from "lucide-react";

export default function TiptapEditorPage() {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
    ],
    content: "<h1>Welcome to <b>TipTap</b>!</h1><p>Now with more formatting.</p>",
    autofocus: true,
    editorProps: {
      attributes: {
        class: "focus:outline-none prose prose-lg max-w-none h-full min-h-[400px]",
        style: "height:100%; width:100%;",
      },
    },
  });

  const setHeading = (level: number) => {
    editor?.chain().focus().toggleHeading({ level }).run();
  };

  const handleSave = () => {
    if (editor) {
      alert(editor.getHTML());
      // Save HTML to backend as needed
    }
  };

  if (!editor) return <div>Loading TipTap...</div>;

  return (
    <div className="fixed inset-0 z-30 bg-white flex flex-col">
      {/* Toolbar */}
      <header className="flex gap-2 items-center bg-gray-100 px-6 py-3 border-b">
        <h1 className="text-xl font-bold mr-6">TipTap Editor</h1>
        {/* Headings dropdown */}
        <div className="relative">
          <select
            value={
              editor.isActive("heading", { level: 1 })
                ? "h1"
                : editor.isActive("heading", { level: 2 })
                ? "h2"
                : editor.isActive("heading", { level: 3 })
                ? "h3"
                : "p"
            }
            onChange={e => {
              const val = e.target.value;
              if (val === "p") editor.chain().focus().setParagraph().run();
              else if (val === "h1") setHeading(1);
              else if (val === "h2") setHeading(2);
              else if (val === "h3") setHeading(3);
            }}
            className="rounded border px-2 py-1 mr-3"
            aria-label="Formatting"
          >
            <option value="p">Paragraph</option>
            <option value="h1">Heading 1</option>
            <option value="h2">Heading 2</option>
            <option value="h3">Heading 3</option>
          </select>
        </div>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("bold") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="Bold"
        >
          <Bold className="w-4 h-4" />
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("italic") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="Italic"
        >
          <Italic className="w-4 h-4" />
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("underline") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          title="Underline"
        >
          <UnderlineIcon className="w-4 h-4" />
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("strike") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleStrike().run()}
          title="Strikethrough"
        >
          <Strikethrough className="w-4 h-4" />
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("code") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleCode().run()}
          title="Inline Code"
        >
          <Code className="w-4 h-4" />
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("blockquote") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          title="Blockquote"
        >
          <Blockquote className="w-4 h-4" />
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("bulletList") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          title="Bullet List"
        >
          <List className="w-4 h-4" />
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${editor.isActive("orderedList") ? "bg-indigo-100" : ""}`}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          title="Numbered List"
        >
          <ListOrdered className="w-4 h-4" />
        </button>
        <button
          type="button"
          className="px-2 py-1 rounded"
          onClick={() => editor.chain().focus().undo().run()}
          title="Undo"
          disabled={!editor.can().undo()}
        >
          <Undo2 className="w-4 h-4" />
        </button>
        <button
          type="button"
          className="px-2 py-1 rounded"
          onClick={() => editor.chain().focus().redo().run()}
          title="Redo"
          disabled={!editor.can().redo()}
        >
          <Redo2 className="w-4 h-4" />
        </button>
        <button
          onClick={handleSave}
          className="ml-auto px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Save
        </button>
      </header>
      {/* Editor */}
      <main className="flex-1 overflow-auto">
        <EditorContent
          editor={editor}
          className="h-full w-full px-8 py-6 focus:outline-none"
          style={{ minHeight: "100%", height: "100%", width: "100%" }}
        />
      </main>
    </div>
  );
}
