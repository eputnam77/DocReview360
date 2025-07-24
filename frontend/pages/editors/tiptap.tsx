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
import SlashCommand from "../extensions/slash-command";
import Lint from "../extensions/lint";
import sanitizeHtml from "../utils/sanitize";
import { TEMPLATES } from "../utils/templates";

// Custom TipTap extensions
import { tiptapHeadingLock } from "../extensions/tiptapHeadingLock";
import { tiptapIndentation } from "../extensions/tiptapIndentation";
import { tiptapSectionNode } from "../extensions/tiptapSectionNode";
import { tiptapWatermark } from "../extensions/tiptapWatermark";
import { tiptapMarkReview } from "../extensions/tiptapMarkReview";

// Yjs for collaboration
import * as Y from "yjs";
import { WebrtcProvider } from "y-webrtc";

// Icons
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
const Loader2 = dynamic(() => import("lucide-react").then((m) => m.Loader2));

interface NewSuggestion {
  from: number;
  to: number;
  original: string;
  suggestion: string;
}

function AiSuggestButton({
  editor,
  aiSuggestEnabled,
  onNewSuggestion,
}: {
  editor: any;
  aiSuggestEnabled: boolean;
  onNewSuggestion?: (data: NewSuggestion) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSuggest() {
    setError(null);
    if (!editor) return;
    setLoading(true);

    const { from, to, empty } = editor.state.selection;
    const selectedText = empty
      ? editor.state.doc.textContent
      : editor.state.doc.textBetween(from, to, " ");

    try {
      const res = await fetch("/api/ai-suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: selectedText,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const { suggestion } = await res.json();

      if (aiSuggestEnabled && onNewSuggestion) {
        onNewSuggestion({ from, to, original: selectedText, suggestion });
      } else {
        editor.chain().focus();
        if (empty) {
          editor.commands.setContent(suggestion);
        } else {
          editor.commands.insertContentAt({ from, to }, suggestion);
        }
      }
    } catch (err: any) {
      setError(err.message || "AI Suggest failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <span className="ml-2 relative">
      <button
        onClick={handleSuggest}
        disabled={loading}
        className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1"
        title="AI Suggest (rewrite selection)"
      >
        {loading ? (
          <Loader2 className="animate-spin w-4 h-4" />
        ) : (
          <span>AI Suggest</span>
        )}
      </button>
      {error && (
        <div className="absolute left-0 mt-2 bg-red-50 text-red-800 px-2 py-1 text-xs rounded shadow z-50">
          {error}
        </div>
      )}
    </span>
  );
}

interface SidebarProps {
  show: boolean;
  onClose: () => void;
  onTemplateLoad: (filename: string) => void;
  onToggleLint: () => void;
  lintEnabled: boolean;
  onToggleCollab: () => void;
  collabEnabled: boolean;
  onToggleAiSuggest: () => void;
  aiSuggestEnabled: boolean;
  onToggleHeadingLock: () => void;
  headingLockEnabled: boolean;
  onToggleIndentation: () => void;
  indentationEnabled: boolean;
  onToggleSectionNode: () => void;
  sectionNodeEnabled: boolean;
  onToggleMarkReview: () => void;
  markReviewEnabled: boolean;
  onToggleWatermark: () => void;
  watermarkEnabled: boolean;
  watermarkText: string;
  onWatermarkText: (text: string) => void;
  suggestions: any[];
  acceptSuggestion: (id: number) => void;
  rejectSuggestion: (id: number) => void;
  clearSuggestions: () => void;
  history: any[];
}

function Sidebar(props: SidebarProps) {
  const {
    show,
    onClose,
    onTemplateLoad,
    onToggleLint,
    lintEnabled,
    onToggleCollab,
    collabEnabled,
    onToggleAiSuggest,
    aiSuggestEnabled,
    onToggleHeadingLock,
    headingLockEnabled,
    onToggleIndentation,
    indentationEnabled,
    onToggleSectionNode,
    sectionNodeEnabled,
    onToggleMarkReview,
    markReviewEnabled,
    onToggleWatermark,
    watermarkEnabled,
    watermarkText,
    onWatermarkText,
    suggestions,
    acceptSuggestion,
    rejectSuggestion,
    clearSuggestions,
    history,
  } = props;
  return (
    <aside
      className={`fixed top-0 right-0 h-full w-80 bg-gray-100 border-l z-50 shadow-lg transform transition-transform duration-200 ${
        show ? "translate-x-0" : "translate-x-full"
      }`}
      style={{ minWidth: "18rem" }}
    >
      <div className="flex justify-between items-center px-4 py-3 border-b bg-white">
        <span className="font-bold text-lg">Tools & Extensions</span>
        <button
          onClick={onClose}
          className="hover:bg-gray-200 rounded p-1"
          aria-label="Close sidebar"
        >
          <XIcon className="w-5 h-5" />
        </button>
      </div>

      <div className="px-4 py-2 space-y-5">
        {/* Templates */}
        <section>
          <div className="font-semibold mb-1">Templates</div>
          <ul className="space-y-1 text-sm">
            {TEMPLATES.map((tpl) => (
              <li key={tpl.filename}>
                <button
                  className="text-indigo-700 underline"
                  onClick={() => onTemplateLoad(tpl.filename)}
                >
                  {tpl.label}
                </button>
              </li>
            ))}
          </ul>
        </section>

        {/* Validation (Lint) */}
        <section>
          <div className="font-semibold mb-1">Validation (Lint)</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              lintEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleLint}
          >
            {lintEnabled ? "Disable Lint" : "Enable Lint"}
          </button>
        </section>

        {/* AI Suggest */}
        <section>
          <div className="font-semibold mb-1 flex items-center gap-1">
            AI Suggest
            {/* Optional info icon, if you have one */}
            {/* <InfoIcon className="w-4 h-4 text-blue-500" /> */}
          </div>
          <button
            className={`px-2 py-1 rounded w-full ${
              aiSuggestEnabled ? "bg-blue-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleAiSuggest}
          >
            {aiSuggestEnabled ? "Disable AI Suggest" : "Enable AI Suggest"}
          </button>
          {aiSuggestEnabled && (
            <div className="mt-2 space-y-2">
              <div className="text-xs text-gray-500 mb-1">
                Select text in the editor and press "AI Suggest" in the toolbar
                to get suggestions.
              </div>
              {suggestions.length === 0 ? (
                <div className="text-xs text-gray-400">
                  No AI suggestions yet.
                </div>
              ) : (
                <div className="space-y-2">
                  {suggestions.map((s) => (
                    <div
                      key={s.id}
                      className="border rounded bg-white px-2 py-1 text-sm"
                    >
                      <div className="mb-1 text-xs text-gray-600">
                        For: <em>{s.original.slice(0, 40)}...</em>
                      </div>
                      <div className="mb-2">{s.suggestion}</div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => acceptSuggestion(s.id)}
                          className="px-2 py-1 rounded bg-green-500 text-white text-xs"
                        >
                          Accept
                        </button>
                        <button
                          onClick={() => rejectSuggestion(s.id)}
                          className="px-2 py-1 rounded bg-red-500 text-white text-xs"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                  <button
                    onClick={clearSuggestions}
                    className="mt-2 text-xs underline text-gray-500"
                  >
                    Clear all suggestions
                  </button>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Heading Lock */}
        <section>
          <div className="font-semibold mb-1">Heading Lock</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              headingLockEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleHeadingLock}
          >
            {headingLockEnabled ? "Disable" : "Enable"} Heading Lock
          </button>
        </section>

        {/* Indentation */}
        <section>
          <div className="font-semibold mb-1">Indentation</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              indentationEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleIndentation}
          >
            {indentationEnabled ? "Disable" : "Enable"} Indentation
          </button>
        </section>

        {/* Section Node */}
        <section>
          <div className="font-semibold mb-1">Section Node</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              sectionNodeEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleSectionNode}
          >
            {sectionNodeEnabled ? "Disable" : "Enable"} Section Node
          </button>
        </section>

        {/* Mark Review */}
        <section>
          <div className="font-semibold mb-1">Mark Review</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              markReviewEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleMarkReview}
          >
            {markReviewEnabled ? "Disable" : "Enable"} Mark Review
          </button>
        </section>

        {/* Watermark */}
        <section>
          <div className="font-semibold mb-1">Watermark</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              watermarkEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleWatermark}
          >
            {watermarkEnabled ? "Disable" : "Enable"} Watermark
          </button>
          {watermarkEnabled && (
            <input
              className="mt-2 w-full border rounded px-2 py-1 text-sm"
              value={watermarkText}
              onChange={(e) => onWatermarkText(e.target.value)}
              placeholder="Watermark text"
            />
          )}
        </section>

        {/* Collaboration */}
        <section>
          <div className="font-semibold mb-1">Collaboration</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              collabEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleCollab}
          >
            {collabEnabled ? "Disconnect" : "Connect"}
          </button>
        </section>

        {/* History */}
        <section>
          <div className="font-semibold mb-1">History</div>
          <ul className="text-xs text-gray-700 space-y-1">
            {history.map((h: any) => (
              <li key={h.id}>{h.label}</li>
            ))}
          </ul>
        </section>
      </div>
    </aside>
  );
}

export default function TipTapEditorPage() {
  // Yjs Setup
  const [collabEnabled, setCollabEnabled] = useState(false);
  const [yDoc, setYDoc] = useState<Y.Doc | null>(null);
  const [provider, setProvider] = useState<any>(null);

  // Lint (validation)
  const [lintEnabled, setLintEnabled] = useState(false);

  // Optional extensions
  const [headingLockEnabled, setHeadingLockEnabled] = useState(false);
  const [indentationEnabled, setIndentationEnabled] = useState(false);
  const [sectionNodeEnabled, setSectionNodeEnabled] = useState(false);
  const [markReviewEnabled, setMarkReviewEnabled] = useState(false);
  const [watermarkEnabled, setWatermarkEnabled] = useState(false);
  const [watermarkText, setWatermarkText] = useState("Sample");

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [aiSuggestEnabled, setAiSuggestEnabled] = useState(false);
  interface Suggestion extends NewSuggestion {
    id: number;
  }
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);

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
          rule: {
            match: ({ tr }) => {
              const issues: any[] = [];
              tr.doc.descendants((node, pos) => {
                // Heading check
                if (node.type.name === "heading") {
                  const text = node.textContent || "";
                  if (!text.trim().endsWith(".")) {
                    issues.push({
                      message: "Heading must end with a period.",
                      from: pos + 1,
                      to: pos + 1 + text.length,
                    });
                  }
                }
                // Prohibited 'DRAFT'
                if (node.textContent && node.textContent.includes("DRAFT")) {
                  const start = node.textContent.indexOf("DRAFT");
                  issues.push({
                    message:
                      '"DRAFT" must not appear in the finalized document.',
                    from: pos + 1 + start,
                    to: pos + 1 + start + 5,
                  });
                }
              });
              // Rule: Missing "1. Purpose." heading
              let foundPurpose = false;
              tr.doc.descendants((node) => {
                if (
                  node.type.name === "heading" &&
                  /^1\. Purpose\./.test(node.textContent)
                ) {
                  foundPurpose = true;
                }
              });
              if (!foundPurpose) {
                issues.push({
                  message: 'Missing required heading: "1. Purpose."',
                  from: 0,
                  to: 1,
                });
              }
              return issues;
            },
          },
        }),
      );
    }
    if (collabEnabled) {
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
          }),
        );
      } else if (yDoc && provider) {
        base.push(
          Collaboration.configure({ document: yDoc }),
          CollaborationCursor.configure({
            provider: provider,
            user: { name: "You", color: "#3b82f6" },
          }),
        );
      }
    }
    if (headingLockEnabled) {
      base.push(tiptapHeadingLock());
    }
    if (indentationEnabled) {
      base.push(tiptapIndentation());
    }
    if (sectionNodeEnabled) {
      base.push(tiptapSectionNode());
    }
    if (markReviewEnabled) {
      base.push(tiptapMarkReview());
    }
    if (watermarkEnabled) {
      base.push(tiptapWatermark(watermarkText));
    }
    return base;
    // eslint-disable-next-line
  }, [
    lintEnabled,
    collabEnabled,
    yDoc,
    provider,
    headingLockEnabled,
    indentationEnabled,
    sectionNodeEnabled,
    markReviewEnabled,
    watermarkEnabled,
    watermarkText,
  ]);

  // TipTap Editor
  const [content, setContent] = useState("<p>Hello world!</p>");
  const editor = useEditor(
    {
      extensions,
      content,
      autofocus: true,
      editorProps: {
        attributes: {
          class:
            "tiptap-content focus:outline-none w-full h-full min-h-[400px] max-w-[860px] mx-auto",
        },
      },
      onUpdate: ({ editor }) => setContent(editor.getHTML()),
    },
    [extensions],
  );

  function getCurrentBlock(editor: any) {
    if (editor.isActive("heading", { level: 1 })) return "h1";
    if (editor.isActive("heading", { level: 2 })) return "h2";
    if (editor.isActive("heading", { level: 3 })) return "h3";
    return "p";
  }
  function setBlock(editor: any, val: string) {
    if (val === "p") editor.chain().focus().setParagraph().run();
    else if (val === "h1")
      editor.chain().focus().toggleHeading({ level: 1 }).run();
    else if (val === "h2")
      editor.chain().focus().toggleHeading({ level: 2 }).run();
    else if (val === "h3")
      editor.chain().focus().toggleHeading({ level: 3 }).run();
  }
  function toolbarButton(
    icon: React.ReactNode,
    command: () => void,
    active: boolean,
    title = "",
  ) {
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

  async function handleTemplateLoad(filename: string) {
    if (!editor) return;
    try {
      const res = await fetch(`/templates/${filename}`);
      if (!res.ok) throw new Error("fetch failed");
      const html = await res.text();
      const sanitized = sanitizeHtml(html);
      editor.commands.setContent(sanitized);
      setContent(sanitized);
    } catch {
      alert("Failed to load template: " + filename);
    }
  }

  function handleToggleLint() {
    setLintEnabled((prev) => !prev);
  }
  function handleToggleCollab() {
    setCollabEnabled((prev) => !prev);
    if (!collabEnabled && yDoc && provider) {
      provider.disconnect();
      setYDoc(null);
      setProvider(null);
    }
  }

  function handleToggleAiSuggest() {
    setAiSuggestEnabled((prev) => !prev);
  }

  function handleToggleHeadingLock() {
    setHeadingLockEnabled((prev) => !prev);
  }
  function handleToggleIndentation() {
    setIndentationEnabled((prev) => !prev);
  }
  function handleToggleSectionNode() {
    setSectionNodeEnabled((prev) => !prev);
  }
  function handleToggleMarkReview() {
    setMarkReviewEnabled((prev) => !prev);
  }
  function handleToggleWatermark() {
    setWatermarkEnabled((prev) => !prev);
  }

  function handleNewSuggestion(data: NewSuggestion) {
    setSuggestions((prev) => [
      ...prev,
      { ...data, id: Date.now() + Math.random() },
    ]);
  }

  function acceptSuggestion(id: number) {
    const s = suggestions.find((x) => x.id === id);
    if (s && editor) {
      editor
        .chain()
        .focus()
        .insertContentAt({ from: s.from, to: s.to }, s.suggestion)
        .run();
    }
    setSuggestions((prev) => prev.filter((x) => x.id !== id));
  }

  function rejectSuggestion(id: number) {
    setSuggestions((prev) => prev.filter((x) => x.id !== id));
  }

  function clearSuggestions() {
    setSuggestions([]);
  }

  function insertTable() {
    editor
      ?.chain()
      .focus()
      .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
      .run();
  }
  function insertImage() {
    const url = prompt("Image URL?");
    if (url) {
      editor?.chain().focus().setImage({ src: url }).run();
    }
  }

  if (!editor)
    return (
      <div className="flex items-center justify-center h-full">
        Loading TipTap…
      </div>
    );

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
          () => editor.chain().focus().toggleUnderline?.().run(),
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
        <AiSuggestButton
          editor={editor}
          aiSuggestEnabled={aiSuggestEnabled}
          onNewSuggestion={handleNewSuggestion}
        />
        <div className="flex-1" />
      </header>

      {/* Lint (Validation) Overlay */}
      {lintEnabled && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-red-50 border border-red-300 px-6 py-2 rounded z-40 shadow">
          <span className="text-red-600 font-semibold">
            Linting enabled — Issues will be highlighted inline.
          </span>
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
        onToggleAiSuggest={handleToggleAiSuggest}
        aiSuggestEnabled={aiSuggestEnabled}
        onToggleHeadingLock={handleToggleHeadingLock}
        headingLockEnabled={headingLockEnabled}
        onToggleIndentation={handleToggleIndentation}
        indentationEnabled={indentationEnabled}
        onToggleSectionNode={handleToggleSectionNode}
        sectionNodeEnabled={sectionNodeEnabled}
        onToggleMarkReview={handleToggleMarkReview}
        markReviewEnabled={markReviewEnabled}
        onToggleWatermark={handleToggleWatermark}
        watermarkEnabled={watermarkEnabled}
        watermarkText={watermarkText}
        onWatermarkText={setWatermarkText}
        suggestions={suggestions}
        acceptSuggestion={acceptSuggestion}
        rejectSuggestion={rejectSuggestion}
        clearSuggestions={clearSuggestions}
        history={DUMMY_HISTORY}
      />
    </div>
  );
}
