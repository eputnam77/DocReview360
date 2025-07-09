import React, { useEffect, useMemo, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Blockquote from "@tiptap/extension-blockquote";
import BoldExtension from "@tiptap/extension-bold";
import BulletList from "@tiptap/extension-bullet-list";
import CodeExtension from "@tiptap/extension-code";
import CodeBlock from "@tiptap/extension-code-block";
import DocumentExtension from "@tiptap/extension-document";
import Dropcursor from "@tiptap/extension-dropcursor";
import Gapcursor from "@tiptap/extension-gapcursor";
import HardBreak from "@tiptap/extension-hard-break";
import Heading from "@tiptap/extension-heading";
import History from "@tiptap/extension-history";
import HorizontalRule from "@tiptap/extension-horizontal-rule";
import ItalicExtension from "@tiptap/extension-italic";
import ListItem from "@tiptap/extension-list-item";
import OrderedList from "@tiptap/extension-ordered-list";
import Paragraph from "@tiptap/extension-paragraph";
import StrikeExtension from "@tiptap/extension-strike";
import TextExtension from "@tiptap/extension-text";
import TextStyle from "@tiptap/extension-text-style";
import { Bold, Italic, Strikethrough, Underline as UnderlineIcon, Code, List, ListOrdered, Quote, Undo2, Redo2 } from "lucide-react";
import FAA_AC_TEMPLATE from "@/data/tiptapTemplates/faa_ac_template";

const AVAILABLE_EXTENSIONS = [
  { name: "StarterKit", extension: StarterKit },
  { name: "Underline", extension: Underline },
  { name: "Document", extension: DocumentExtension },
  { name: "Paragraph", extension: Paragraph },
  { name: "Text", extension: TextExtension },
  { name: "History", extension: History },
  { name: "Bold", extension: BoldExtension },
  { name: "Italic", extension: ItalicExtension },
  { name: "Strike", extension: StrikeExtension },
  { name: "Heading", extension: Heading },
  { name: "Code", extension: CodeExtension },
  { name: "CodeBlock", extension: CodeBlock },
  { name: "Blockquote", extension: Blockquote },
  { name: "BulletList", extension: BulletList },
  { name: "OrderedList", extension: OrderedList },
  { name: "ListItem", extension: ListItem },
  { name: "HardBreak", extension: HardBreak },
  { name: "HorizontalRule", extension: HorizontalRule },
  { name: "Dropcursor", extension: Dropcursor },
  { name: "Gapcursor", extension: Gapcursor },
  { name: "TextStyle", extension: TextStyle },
];

// Import the TipTap-specific CSS
import "@/styles/tiptap.css";

export default function TiptapEditorPage() {
  const [enabledExtensions, setEnabledExtensions] = useState<string[]>(() => {
    if (typeof window === "undefined") return AVAILABLE_EXTENSIONS.map(e => e.name);
    const stored = localStorage.getItem("tiptapExtensions");
    return stored ? JSON.parse(stored) : AVAILABLE_EXTENSIONS.map(e => e.name);
  });

  const extensions = useMemo(
    () =>
      AVAILABLE_EXTENSIONS.filter(e => enabledExtensions.includes(e.name)).map(
        e => e.extension,
      ),
    [enabledExtensions],
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("tiptapExtensions", JSON.stringify(enabledExtensions));
    }
  }, [enabledExtensions]);

  const editor = useEditor(
    {
      extensions,
      content: FAA_AC_TEMPLATE,
      autofocus: true,
      editorProps: {
        attributes: {
          class: "tiptap-content focus:outline-none w-full h-full",
        },
      },
    },
    [extensions],
  );

  const setHeading = (level: number) => {
    editor?.chain().focus().toggleHeading({ level }).run();
  };

  const toggleExtension = (name: string) => {
    setEnabledExtensions(prev =>
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name],
    );
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
        <div className="flex gap-3 mr-6">
          {AVAILABLE_EXTENSIONS.map(ext => (
            <label key={ext.name} className="flex items-center gap-1 text-sm">
              <input
                type="checkbox"
                checked={enabledExtensions.includes(ext.name)}
                onChange={() => toggleExtension(ext.name)}
              />
              {ext.name}
            </label>
          ))}
        </div>
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
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("bold") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleBold().run()} title="Bold"><Bold className="w-4 h-4" /></button>
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("italic") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleItalic().run()} title="Italic"><Italic className="w-4 h-4" /></button>
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("underline") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleUnderline().run()} title="Underline"><UnderlineIcon className="w-4 h-4" /></button>
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("strike") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleStrike().run()} title="Strikethrough"><Strikethrough className="w-4 h-4" /></button>
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("code") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleCode().run()} title="Inline Code"><Code className="w-4 h-4" /></button>
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("blockquote") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleBlockquote().run()} title="Blockquote"><Quote className="w-4 h-4" /></button>
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("bulletList") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleBulletList().run()} title="Bullet List"><List className="w-4 h-4" /></button>
        <button type="button" className={`px-2 py-1 rounded ${editor.isActive("orderedList") ? "bg-indigo-100" : ""}`} onClick={() => editor.chain().focus().toggleOrderedList().run()} title="Numbered List"><ListOrdered className="w-4 h-4" /></button>
        <button type="button" className="px-2 py-1 rounded" onClick={() => editor.chain().focus().undo().run()} title="Undo" disabled={!editor.can().undo()}><Undo2 className="w-4 h-4" /></button>
        <button type="button" className="px-2 py-1 rounded" onClick={() => editor.chain().focus().redo().run()} title="Redo" disabled={!editor.can().redo()}><Redo2 className="w-4 h-4" /></button>
        <button onClick={handleSave} className="ml-auto px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">Save</button>
      </header>
      {/* Editor */}
      <main className="flex-1 overflow-auto">
        <EditorContent editor={editor} className="tiptap-content" />
      </main>
    </div>
  );
}
