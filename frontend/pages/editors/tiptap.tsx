// TipTapEditorPage.tsx

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { EditorContent, useEditor } from "@tiptap/react";

// Core Extensions
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import Image from "@tiptap/extension-image";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";

// Slash command & Linting (Validation)
import SlashCommand from "@tiptap/extension-slash-command";
import Lint from "@tiptap/extension-lint";

// Yjs for collaboration
import * as Y from "yjs";
import { WebrtcProvider } from "y-webrtc";

// Icons (lucide-react)
const Bold = dynamic(() => import("lucide-react").then((m) => m.Bold));
const Italic = dynamic(() => import("lucide-react").then((m) => m.Italic));
const UnderlineIcon = dynamic(() =>
  import("lucide-react").then((m) => m.Underline),
);
const Strikethrough = dynamic(() =>
  import("lucide-react").then((m) => m.Strikethrough),
);
const Code = dynamic(() => import("lucide-react").then((m) => m.Code));
const Quote = dynamic(() => import("lucide-react").then((m) => m.Quote));
const List = dynamic(() => import("lucide-react").then((m) => m.List));
const ListOrdered = dynamic(() =>
  import("lucide-react").then((m) => m.ListOrdered),
);
const Undo2 = dynamic(() => import("lucide-react").then((m) => m.Undo2));
const Redo2 = dynamic(() => import("lucide-react").then((m) => m.Redo2));
const ImageIcon = dynamic(() => import("lucide-react").then((m) => m.Image));
const TableIcon = dynamic(() => import("lucide-react").then((m) => m.Table));
const MenuIcon = dynamic(() => import("lucide-react").then((m) => m.Menu));
const XIcon = dynamic(() => import("lucide-react").then((m) => m.X));

// Sidebar controls example (replace with your own as needed)
function Sidebar({
  show,
  onClose,
  onTemplateLoad,
  onToggleLint,
  lintEnabled,
  onToggleCollab,
  collabEnabled,
  history,
}) {
  return (
    <aside
      className={`fixed top-0 right-0 h-full w-80 bg-gray-100 border-l z-50 shadow-lg transform transition-transform duration-200 ${
        show ? "translate-x-0" : "translate-x-full"
      }`}
      style={{ minWidth: "18rem" }}
    >
      <div className="flex justify-between items-center px-4 py-3 border-b">
        <span className="font-bold">Tools & Extensions</span>
        <button
          onClick={onClose}
          className="hover:bg-gray-300 rounded p-1"
          aria-label="Close"
        >
          <XIcon className="w-5 h-5" />
        </button>
      </div>
      <div className="px-4 py-2">
        <div className="mb-4">
          <div className="font-semibold mb-1">Templates</div>
          <button
            className="text-indigo-700 underline"
            onClick={() => onTemplateLoad("sample")}
          >
            Load Sample Template
          </button>
        </div>
        <div className="mb-4">
          <div className="font-semibold mb-1">Validation (Lint)</div>
          <button
            className={`px-2 py-1 rounded ${lintEnabled ? "bg-green-500 text-white" : "bg-gray-200"}`}
            onClick={onToggleLint}
          >
            {lintEnabled ? "Disable" : "Enable"} Lint
          </button>
        </div>
        <div className="mb-4">
          <div className="font-semibold mb-1">Collaboration</div>
          <button
            className={`px-2 py-1 rounded ${collabEnabled ? "bg-green-500 text-white" : "bg-gray-200"}`}
            onClick={onToggleCollab}
          >
            {collabEnabled ? "Disconnect" : "Connect"}
          </button>
        </div>
        <div>
          <div className="font-semibold mb-1">History</div>
          <ul className="text-xs">
            {history.map((h) => (
              <li key={h.id}>{h.label}</li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}

export default function TipTapEditorPage() {
  // Yjs Setup (for demo purposes)
  const [collabEnabled, setCollabEnabled] = useState(false);
  const [yDoc, setYDoc] = useState(null as null | Y.Doc);
  const [provider, setProvider] = useState<any>(null);

  // Lint (validation)
  const [lintEnabled, setLintEnabled] = useState(false);

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Version History (dummy)
  const DUMMY_HISTORY = [
    { id: 1, label: "Draft - Jul 9, 8:00 am" },
    { id: 2, label: "AutoSave - Jul 8, 3:30 pm" },
    { id: 3, label: "Submitted - Jul 7, 12:15 pm" },
  ];

  // Editor Extensions
  const extensions = useMemo(() => {
    const base = [
      StarterKit,
      Underline,
      Table.configure({ resizable: true }),
      TableRow,
      TableCell,
      TableHeader,
      Image,
      SlashCommand,
    ];
    if (lintEnabled) {
      base.push(
        Lint.configure({
          // Linting rules per https://tiptap.dev/docs/examples/experiments/linting
          rule: {
            match: ({ tr }) => {
              const text = tr.doc.textContent;
              // Simple example: flag "foo"
              const issues = [];
              if (text.includes("foo")) {
                issues.push({
                  message: "Please avoid the word 'foo'.",
                  from: text.indexOf("foo"),
                  to: text.indexOf("foo") + 3,
                  fix: (view, from, to) => {
                    view.dispatch(
                      view.state.tr.insertText("bar", from, to)
                    );
                  },
                });
              }
              return issues;
            },
          },
        })
      );
    }
    if (collabEnabled) {
      // Ensure Yjs provider is ready
      if (!yDoc) {
        const doc = new Y.Doc();
        const webrtcProvider = new WebrtcProvider("tiptap-demo-room", doc);
        setYDoc(doc);
        setProvider(webrtcProvider);
        base.push(
          Collaboration.configure({ document: doc }),
          CollaborationCursor.configure({
            provider: webrtcProvider,
            user: { name: "You", color: "#3b82f6" },
          })
        );
      } else if (yDoc && provider) {
        base.push(
          Collaboration.configure({ document: yDoc }),
          CollaborationCursor.configure({
            provider: provider,
            user: { name: "You", color: "#3b82f6" },
          })
        );
      }
    }
    return base;
    // eslint-disable-next-line
  }, [lintEnabled, collabEnabled, yDoc, provider]);

  // TipTap Editor
  const [content, setContent] = useState("<p>Hello world!</p>");
  const editor = useEditor({
    extensions,
    content,
    autofocus: true,
    editorProps: {
      attributes: {
        class: "tiptap-content focus:outline-none w-full h-full min-h-[400px] max-w-[860px] mx-auto",
      },
    },
    onUpdate: ({ editor }) => setContent(editor.getHTML()),
  });

  // Toolbar Helpers
  function getCurrentBlock(editor) {
    if (editor.isActive("heading", { level: 1 })) return "h1";
    if (editor.isActive("heading", { level: 2 })) return "h2";
    if (editor.isActive("heading", { level: 3 })) return "h3";
    return "p";
  }
  function setBlock(editor, val) {
    if (val === "p") editor.chain().focus().setParagraph().run();
    else if (val === "h1") editor.chain().focus().toggleHeading({ level: 1 }).run();
    else if (val === "h2") editor.chain().focus().toggleHeading({ level: 2 }).run();
    else if (val === "h3") editor.chain().focus().toggleHeading({ level: 3 }).run();
  }
  function toolbarButton(icon, command, active, title = "") {
    return (
      <button
        type="button"
        className={`p-2 rounded ${active ? "bg-indigo-100" : ""}`}
        onClick={command}
        title={title}
      >
        {icon}
      </button>
    );
  }

  // Template loading (dummy)
  function handleTemplateLoad(name: string) {
    if (!editor) return;
    if (name === "sample") {
      editor.commands.setContent(
        "<h1>Sample Template</h1><p>This is a loaded template.</p>"
      );
    }
  }

  // Lint/validation toggle
  function handleToggleLint() {
    setLintEnabled((prev) => !prev);
  }
  // Collab toggle
  function handleToggleCollab() {
    setCollabEnabled((prev) => !prev);
    if (!collabEnabled && yDoc && provider) {
      // Clean up Yjs on disconnect
      provider.disconnect();
      setYDoc(null);
      setProvider(null);
    }
  }

  // Table/image actions
  function insertTable() {
    editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  }
  function insertImage() {
    const url = prompt("Image URL?");
    if (url) {
      editor?.chain().focus().setImage({ src: url }).run();
    }
  }

  if (!editor)
    return <div className="flex items-center justify-center h-full">Loading TipTap…</div>;

  return (
    <div className="flex flex-col h-screen w-full bg-white">
      {/* Header Toolbar */}
      <header className="flex items-center gap-2 bg-gray-100 px-6 py-3 border-b w-full">
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 rounded bg-gray-200 mr-2"
          aria-label="Open sidebar"
        >
          <MenuIcon className="w-5 h-5" />
        </button>
        <span className="text-xl font-bold">TipTap Editor</span>
        <select
          value={getCurrentBlock(editor)}
          onChange={(e) => setBlock(editor, e.target.value)}
          className="rounded border px-2 py-1 ml-4"
          aria-label="Block style"
        >
          <option value="p">Paragraph</option>
          <option value="h1">Heading 1</option>
          <option value="h2">Heading 2</option>
          <option value="h3">Heading 3</option>
        </select>
        {toolbarButton(<Bold className="w-4 h-4" />, () => editor.chain().focus().toggleBold().run(), editor.isActive("bold"), "Bold")}
        {toolbarButton(<Italic className="w-4 h-4" />, () => editor.chain().focus().toggleItalic().run(), editor.isActive("italic"), "Italic")}
        {toolbarButton(<UnderlineIcon className="w-4 h-4" />, () => editor.chain().focus().toggleUnderline?.().run(), editor.isActive("underline"), "Underline")}
        {toolbarButton(<Strikethrough className="w-4 h-4" />, () => editor.chain().focus().toggleStrike().run(), editor.isActive("strike"), "Strikethrough")}
        {toolbarButton(<Code className="w-4 h-4" />, () => editor.chain().focus().toggleCode().run(), editor.isActive("code"), "Inline Code")}
        {toolbarButton(<Quote className="w-4 h-4" />, () => editor.chain().focus().toggleBlockquote().run(), editor.isActive("blockquote"), "Blockquote")}
        {toolbarButton(<List className="w-4 h-4" />, () => editor.chain().focus().toggleBulletList().run(), editor.isActive("bulletList"), "Bullet List")}
        {toolbarButton(<ListOrdered className="w-4 h-4" />, () => editor.chain().focus().toggleOrderedList().run(), editor.isActive("orderedList"), "Numbered List")}
        {toolbarButton(<Undo2 className="w-4 h-4" />, () => editor.chain().focus().undo().run(), false, "Undo")}
        {toolbarButton(<Redo2 className="w-4 h-4" />, () => editor.chain().focus().redo().run(), false, "Redo")}
        <button
          onClick={insertTable}
          className="ml-2 p-2 rounded bg-gray-200"
          title="Insert Table"
        >
          <TableIcon className="w-4 h-4" />
        </button>
        <button
          onClick={insertImage}
          className="ml-1 p-2 rounded bg-gray-200"
          title="Insert Image"
        >
          <ImageIcon className="w-4 h-4" />
        </button>
        <button
          onClick={() => alert(editor.getHTML())}
          className="ml-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Save
        </button>
        <div className="flex-1" />
        {/* Optionally, more header controls */}
      </header>

      {/* Lint (Validation) Overlay */}
      {lintEnabled && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-red-50 border border-red-300 px-6 py-2 rounded z-40 shadow">
          <span className="text-red-600 font-semibold">Linting enabled — Issues will be highlighted inline.</span>
        </div>
      )}

      {/* Main Editor */}
      <main className="flex-1 overflow-auto flex justify-center items-start bg-white">
        <div className="w-full max-w-[860px] p-8">
          <EditorContent editor={editor} />
        </div>
      </main>

      {/* Sidebar for templates, validation, collab, history */}
      <Sidebar
        show={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onTemplateLoad={handleTemplateLoad}
        onToggleLint={handleToggleLint}
        lintEnabled={lintEnabled}
        onToggleCollab={handleToggleCollab}
        collabEnabled={collabEnabled}
        history={DUMMY_HISTORY}
      />
    </div>
  );
}
