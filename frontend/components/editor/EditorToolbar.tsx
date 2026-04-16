import React from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { toolbarButton } from "../ToolbarButton";
import InsertMenu from "../InsertMenu";
import AiSuggestButton from "./AiSuggestButton";
import type { NewSuggestion } from "@/lib/useEditorSuggestions";
import type { ValidationSummary } from "@/lib/useEditorSave";
import type { SaveStatus } from "@/lib/useEditorSave";
import { canRunEditorCommand, runEditorCommand } from "@/lib/tiptapCommandUtils";

const Bold = dynamic(() => import("lucide-react").then((m) => m.Bold));
const Italic = dynamic(() => import("lucide-react").then((m) => m.Italic));
const UnderlineIcon = dynamic(() => import("lucide-react").then((m) => m.Underline));
const Strikethrough = dynamic(() => import("lucide-react").then((m) => m.Strikethrough));
const Code = dynamic(() => import("lucide-react").then((m) => m.Code));
const Quote = dynamic(() => import("lucide-react").then((m) => m.Quote));
const List = dynamic(() => import("lucide-react").then((m) => m.List));
const ListOrdered = dynamic(() => import("lucide-react").then((m) => m.ListOrdered));
const Undo2 = dynamic(() => import("lucide-react").then((m) => m.Undo2));
const Redo2 = dynamic(() => import("lucide-react").then((m) => m.Redo2));
const MenuIcon = dynamic(() => import("lucide-react").then((m) => m.Menu));
const IndentIncrease = dynamic(() => import("lucide-react").then((m) => m.IndentIncrease));
const IndentDecrease = dynamic(() => import("lucide-react").then((m) => m.IndentDecrease));

function getCurrentBlock(editor: any) {
  if (editor.isActive("heading", { level: 1 })) return "h1";
  if (editor.isActive("heading", { level: 2 })) return "h2";
  if (editor.isActive("heading", { level: 3 })) return "h3";
  return "p";
}

function setBlock(editor: any, val: string) {
  if (val === "p") editor.chain().focus().setParagraph().run();
  else if (val === "h1") editor.chain().focus().setHeading({ level: 1 }).run();
  else if (val === "h2") editor.chain().focus().setHeading({ level: 2 }).run();
  else if (val === "h3") editor.chain().focus().setHeading({ level: 3 }).run();
}

export interface EditorToolbarProps {
  editor: any;
  // Online / sync state
  isOnline: boolean;
  pendingCount: number;
  // Save state
  saveStatus: SaveStatus;
  pdfUrl: string | null;
  validationSummary: ValidationSummary | null;
  docId: string | undefined;
  // Template state
  formattingLocked: boolean;
  showTemplatePicker: boolean;
  setShowTemplatePicker: React.Dispatch<React.SetStateAction<boolean>>;
  templatePickerRef: React.RefObject<HTMLDivElement | null>;
  templates: any[];
  projectDocType: string | null;
  handleTemplateLoad: (filename: string) => Promise<void>;
  // Sidebar
  onOpenSidebar: () => void;
  // Extensions
  indentationEnabled: boolean;
  // AI suggestions
  aiSuggestEnabled: boolean;
  onNewSuggestion: (data: NewSuggestion) => void;
  // Submit
  onSubmit: () => void;
  // Insert helpers
  insertTable: () => void;
  insertImage: () => void;
}

export default function EditorToolbar({
  editor,
  isOnline,
  pendingCount,
  saveStatus,
  pdfUrl,
  validationSummary,
  docId,
  formattingLocked,
  showTemplatePicker,
  setShowTemplatePicker,
  templatePickerRef,
  templates,
  projectDocType,
  handleTemplateLoad,
  onOpenSidebar,
  indentationEnabled,
  aiSuggestEnabled,
  onNewSuggestion,
  onSubmit,
  insertTable,
  insertImage,
}: EditorToolbarProps) {
  return (
    <header className="flex items-center gap-2 bg-gray-100 px-6 py-3 border-b w-full">
      <button
        onClick={onOpenSidebar}
        className="p-2 rounded bg-gray-200 mr-2"
        aria-label="Open sidebar"
        role="button"
      >
        <MenuIcon className="w-5 h-5" />
      </button>
      <span className="text-xl font-bold">TipTap Editor</span>

      {!isOnline && (
        <span className="text-xs text-yellow-800 bg-yellow-200 px-2 py-1 rounded font-semibold">
          Offline
        </span>
      )}
      {formattingLocked && (
        <span className="text-xs text-amber-700 bg-amber-100 px-2 py-1 rounded">
          Template formatting locked
        </span>
      )}

      <select
        value={getCurrentBlock(editor)}
        onChange={(e) => setBlock(editor, e.target.value)}
        className={`rounded border px-2 py-1 ml-4 ${formattingLocked ? "opacity-50 cursor-not-allowed" : ""}`}
        aria-label="Block style"
        disabled={formattingLocked}
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
      {toolbarButton(<Quote className="w-4 h-4" />, () => editor.chain().focus().toggleBlockquote().run(), editor.isActive("blockquote"), "Blockquote", formattingLocked)}
      {toolbarButton(<List className="w-4 h-4" />, () => editor.chain().focus().toggleBulletList().run(), editor.isActive("bulletList"), "Bullet List", formattingLocked)}
      {toolbarButton(<ListOrdered className="w-4 h-4" />, () => editor.chain().focus().toggleOrderedList().run(), editor.isActive("orderedList"), "Numbered List", formattingLocked)}

      {toolbarButton(
        <IndentIncrease className="w-4 h-4" />,
        () => {
          if (indentationEnabled && canRunEditorCommand(editor, "indent")) {
            runEditorCommand(editor, "indent");
          } else {
            editor.chain().focus().sinkListItem("listItem").run();
          }
        },
        false, "Indent", formattingLocked,
      )}
      {toolbarButton(
        <IndentDecrease className="w-4 h-4" />,
        () => {
          if (indentationEnabled && canRunEditorCommand(editor, "outdent")) {
            runEditorCommand(editor, "outdent");
          } else {
            editor.chain().focus().liftListItem("listItem").run();
          }
        },
        false, "Outdent", formattingLocked,
      )}

      {toolbarButton(<Undo2 className="w-4 h-4" />, () => editor.chain().focus().undo().run(), false, "Undo")}
      {toolbarButton(<Redo2 className="w-4 h-4" />, () => editor.chain().focus().redo().run(), false, "Redo")}

      <InsertMenu insertTable={insertTable} insertImage={insertImage} disabled={formattingLocked} />

      {/* Templates quick-picker */}
      <div className="relative" ref={templatePickerRef}>
        <button
          onClick={() => setShowTemplatePicker((v) => !v)}
          className={`p-2 rounded border text-sm ${showTemplatePicker ? "bg-indigo-100 border-indigo-400" : "bg-gray-200 border-gray-300"}`}
          aria-label="Open template picker"
          title="Apply a template"
        >
          Templates
        </button>
        {showTemplatePicker && (
          <div className="absolute top-full mt-1 left-0 z-50 bg-white border border-gray-200 rounded shadow-lg min-w-[200px] max-h-64 overflow-y-auto">
            <div className="px-3 py-2 text-xs font-semibold text-gray-500 border-b">
              {projectDocType ? `Templates for: ${projectDocType}` : "All templates"}
            </div>
            {templates
              .filter((t) => {
                if (!projectDocType) return true;
                const tDocType = (t.docType || t.doc_type || t.type || "").trim().toLowerCase();
                return !tDocType || tDocType === projectDocType.trim().toLowerCase();
              })
              .map((tpl) => (
                <button
                  key={tpl.id || tpl.name}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 focus:bg-indigo-50"
                  onClick={() => {
                    setShowTemplatePicker(false);
                    handleTemplateLoad(tpl.id || tpl.name);
                  }}
                >
                  {tpl.label || tpl.name || tpl.id}
                </button>
              ))}
            {templates.filter((t) => {
              if (!projectDocType) return true;
              const tDocType = (t.docType || t.doc_type || t.type || "").trim().toLowerCase();
              return !tDocType || tDocType === projectDocType.trim().toLowerCase();
            }).length === 0 && (
              <div className="px-3 py-2 text-sm text-gray-400">No templates available.</div>
            )}
          </div>
        )}
      </div>

      <button
        onClick={onSubmit}
        className="ml-4 px-2 py-1 border rounded bg-indigo-600 text-white hover:bg-indigo-700"
        title="Save a final revision and mark as submitted for review"
      >
        Submit
      </button>

      <div className="ml-4 text-sm text-gray-600">
        {isOnline && pendingCount > 0
          ? "Syncing…"
          : saveStatus === "saving"
          ? "Saving…"
          : saveStatus === "saved"
          ? "Saved"
          : saveStatus === "error"
          ? "Error"
          : saveStatus === "offline"
          ? "Offline"
          : ""}
      </div>

      {pdfUrl && (
        <div className="ml-4 text-sm text-gray-600">
          Archived •{" "}
          <a href={pdfUrl} className="underline" target="_blank" rel="noopener noreferrer">
            download PDF
          </a>
        </div>
      )}

      {validationSummary && (
        <Link
          href={
            docId
              ? `/tools/document-quality?document_id=${encodeURIComponent(docId)}`
              : "/tools/document-quality"
          }
          title={`Quality score: ${validationSummary.score != null ? Math.round(validationSummary.score * 100) : "N/A"}% | Grade: ${validationSummary.grade ?? "N/A"} | Issues: ${validationSummary.issue_count ?? 0} — Click to view full report`}
          className={`ml-3 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium hover:opacity-80 ${
            (validationSummary.score ?? 0) >= 0.8
              ? "bg-green-50 border-green-200 text-green-600"
              : (validationSummary.score ?? 0) >= 0.5
              ? "bg-amber-50 border-amber-200 text-amber-600"
              : "bg-red-50 border-red-200 text-red-600"
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          {validationSummary.score != null
            ? `${Math.round(validationSummary.score * 100)}% — ${
                (validationSummary.score ?? 0) >= 0.8
                  ? "Good"
                  : (validationSummary.score ?? 0) >= 0.5
                  ? "Needs attention"
                  : "Issues found"
              }`
            : validationSummary.issue_count != null
            ? `${validationSummary.issue_count} issues`
            : "Validated"}
        </Link>
      )}

      <AiSuggestButton editor={editor} aiSuggestEnabled={aiSuggestEnabled} onNewSuggestion={onNewSuggestion} />

      <div className="flex-1" />
    </header>
  );
}
