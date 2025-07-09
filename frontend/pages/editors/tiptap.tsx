// frontend/pages/editors/tiptap.tsx

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
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
import {
  Bold,
  Italic,
  Strikethrough,
  Underline as UnderlineIcon,
  Code,
  List,
  ListOrdered,
  Quote,
  Undo2,
  Redo2,
  ChevronDown,
  ChevronUp,
  Clock,
} from "lucide-react";
import FAA_AC_TEMPLATE from "@/data/tiptapTemplates/faa_ac_template";
import "@/styles/tiptap.css";

// --- Extension Management ---
const AVAILABLE_EXTENSIONS = [
  { name: "StarterKit", extension: StarterKit.configure({ history: false }) },
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

// --- Extensions Default ---
const DEFAULT_TOOLBAR_EXTENSIONS = [
  "StarterKit",
  "Underline",
  "Document",
  "Paragraph",
  "Text",
  "History",
  "Bold",
  "Italic",
  "Strike",
  "Heading",
  "Code",
  "CodeBlock",
  "Blockquote",
  "BulletList",
  "OrderedList",
  "ListItem",
  "HardBreak",
];

function TiptapEditorPage() {
  // --- Extensions (hidden in a menu) ---
  const [showExtensionMenu, setShowExtensionMenu] = useState(false);
  const [enabledExtensions, setEnabledExtensions] = useState<string[]>(() => {
    if (typeof window === "undefined") return DEFAULT_TOOLBAR_EXTENSIONS;
    const stored = localStorage.getItem("tiptapExtensions");
    return stored ? JSON.parse(stored) : DEFAULT_TOOLBAR_EXTENSIONS;
  });

  const extensions = useMemo(
    () =>
      AVAILABLE_EXTENSIONS.filter((e) =>
        enabledExtensions.includes(e.name),
      ).map((e) => e.extension),
    [enabledExtensions],
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(
        "tiptapExtensions",
        JSON.stringify(enabledExtensions),
      );
    }
  }, [enabledExtensions]);

  // --- Editor ---
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

  const handleSave = () => {
    if (editor) {
      alert(editor.getHTML());
      // Integrate with your backend as needed.
    }
  };

  // --- Toolbar Button (icon, command, active?) ---
  const toolbarButton = (
    icon: any,
    command: () => void,
    active: boolean,
    title = "",
  ) => (
    <button
      type="button"
      className={`px-2 py-1 rounded ${active ? "bg-indigo-100" : ""}`}
      onClick={command}
      title={title}
    >
      {icon}
    </button>
  );

  // --- Dummy Version History (replace with actual integration) ---
  const [showHistory, setShowHistory] = useState(false);
  const DUMMY_HISTORY = [
    { id: 1, label: "Draft - Jul 9, 8:00am" },
    { id: 2, label: "AutoSave - Jul 8, 3:30pm" },
    { id: 3, label: "Submitted - Jul 7, 12:15pm" },
  ];

  if (!editor) return <div>Loading TipTap...</div>;

  return (
    <div className="fixed inset-0 z-30 bg-white flex flex-col">
      {/* Toolbar */}
      <header className="flex items-center gap-2 bg-gray-100 px-6 py-3 border-b w-full">
        <h1 className="text-xl font-bold mr-6">TipTap Editor</h1>

        {/* Formatting toolbar */}
        <div className="flex items-center gap-1">
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
            onChange={(e) => {
              const val = e.target.value;
              if (val === "p") editor.chain().focus().setParagraph().run();
              else if (val === "h1") setHeading(1);
              else if (val === "h2") setHeading(2);
              else if (val === "h3") setHeading(3);
            }}
            className="rounded border px-2 py-1"
            aria-label="Formatting"
          >
            <option value="p">Paragraph</option>
            <option value="h1">Heading 1</option>
            <option value="h2">Heading 2</option>
            <option value="h3">Heading 3</option>
          </select>
          {toolbarButton(
            <Bold className="w-4 h-4" />,
            () => editor.chain().focus().toggleBold().run(),
            editor.isActive("bold"),
            "Bold",
          )}
          {toolbarButton(
            <Italic className="w-4 h-4" />,
            () => editor.chain().focus().toggleItalic().run(),
            editor.isActive("italic"),
            "Italic",
          )}
          {toolbarButton(
            <UnderlineIcon className="w-4 h-4" />,
            () => editor.chain().focus().toggleUnderline().run(),
            editor.isActive("underline"),
            "Underline",
          )}
          {toolbarButton(
            <Strikethrough className="w-4 h-4" />,
            () => editor.chain().focus().toggleStrike().run(),
            editor.isActive("strike"),
            "Strikethrough",
          )}
          {toolbarButton(
            <Code className="w-4 h-4" />,
            () => editor.chain().focus().toggleCode().run(),
            editor.isActive("code"),
            "Inline Code",
          )}
          {toolbarButton(
            <Quote className="w-4 h-4" />,
            () => editor.chain().focus().toggleBlockquote().run(),
            editor.isActive("blockquote"),
            "Blockquote",
          )}
          {toolbarButton(
            <List className="w-4 h-4" />,
            () => editor.chain().focus().toggleBulletList().run(),
            editor.isActive("bulletList"),
            "Bullet List",
          )}
          {toolbarButton(
            <ListOrdered className="w-4 h-4" />,
            () => editor.chain().focus().toggleOrderedList().run(),
            editor.isActive("orderedList"),
            "Numbered List",
          )}
          {toolbarButton(
            <Undo2 className="w-4 h-4" />,
            () => editor.chain().focus().undo().run(),
            false,
            "Undo",
          )}
          {toolbarButton(
            <Redo2 className="w-4 h-4" />,
            () => editor.chain().focus().redo().run(),
            false,
            "Redo",
          )}
          <button
            onClick={handleSave}
            className="ml-2 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Save
          </button>
        </div>

        {/* Spacer */}
        <div className="flex-1"></div>

        {/* Extensions menu (hidden, only advanced users) */}
        <div className="relative">
          <button
            onClick={() => setShowExtensionMenu(!showExtensionMenu)}
            className="px-3 py-1 border rounded bg-gray-50 hover:bg-gray-200 flex items-center gap-1"
            title="Manage Extensions"
          >
            Extensions <ChevronDown className="w-4 h-4" />
          </button>
          {showExtensionMenu && (
            <div className="absolute right-0 mt-2 bg-white shadow-lg border rounded p-4 z-50 max-h-72 overflow-y-auto w-64">
              <div className="mb-2 font-semibold">Enabled Extensions</div>
              {AVAILABLE_EXTENSIONS.map((ext) => (
                <label
                  key={ext.name}
                  className="flex items-center gap-2 text-sm my-1"
                >
                  <input
                    type="checkbox"
                    checked={enabledExtensions.includes(ext.name)}
                    onChange={() => {
                      setEnabledExtensions((prev) =>
                        prev.includes(ext.name)
                          ? prev.filter((n) => n !== ext.name)
                          : [...prev, ext.name],
                      );
                    }}
                  />
                  {ext.name}
                </label>
              ))}
              <button
                className="mt-2 text-xs px-2 py-1 rounded bg-gray-200"
                onClick={() => setShowExtensionMenu(false)}
              >
                Close
              </button>
            </div>
          )}
        </div>

        {/* Version History */}
        <div className="relative ml-4">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="px-3 py-1 border rounded bg-gray-50 hover:bg-gray-200 flex items-center gap-1"
            title="Version History"
          >
            <Clock className="w-4 h-4" />
            History
            {showHistory ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {showHistory && (
            <div className="absolute right-0 mt-2 bg-white shadow-lg border rounded p-2 z-50 w-56">
              <div className="mb-2 font-semibold">Version History</div>
              <ul>
                {DUMMY_HISTORY.map((v) => (
                  <li
                    key={v.id}
                    className="py-1 border-b last:border-none text-xs"
                  >
                    {v.label}
                  </li>
                ))}
              </ul>
              <button
                className="mt-2 text-xs px-2 py-1 rounded bg-gray-200"
                onClick={() => setShowHistory(false)}
              >
                Close
              </button>
            </div>
          )}
        </div>
      </header>
      {/* Editor */}
      <main className="flex-1 overflow-auto">
        <EditorContent editor={editor} className="tiptap-content" />
      </main>
    </div>
  );
}

// Disable SSR for Next.js hydration issues
export default dynamic(() => Promise.resolve(TiptapEditorPage), { ssr: false });
