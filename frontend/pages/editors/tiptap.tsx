import { EditorContent, useEditor } from "@tiptap/react";
import { Extension } from "@tiptap/core";
import dynamic from "next/dynamic";
import { useRouter } from "next/router";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { generateDiffHtml } from "../../utils/diff";
import { logSaveError, isOffline } from "@/utils/saveStatus";
import { useOfflineSync } from "@/lib/useOfflineSync";
import { saveOfflineDraft } from "@/lib/offlineStorage";

import ExtensionsPanel, { ExtensionItem, ExtensionStatus } from "../../components/ExtensionsPanel";
import InsertMenu from "../../components/InsertMenu";
import { toolbarButton } from "../../components/ToolbarButton";

// Core Extensions
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import Image from "@tiptap/extension-image";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import Underline from "@tiptap/extension-underline";
import StarterKit from "@tiptap/starter-kit";
import SlashCommand from "../../extensions/tiptapSlashCommand";
import sanitizeHtml from "../../utils/sanitize";
import { resolveStarterContent } from "@/lib/starterContent";
import { canRunEditorCommand, runEditorCommand } from "@/lib/tiptapCommandUtils";
import { API, authenticatedFetch } from "@/lib/api";
import { buildTemplateUrlPath } from "@/lib/templatePath";
import { useUserStore } from "@/state/user";

// Custom TipTap extensions
import { tiptapStructure } from "../../extensions/tiptapStructure";

// Hocuspocus provider for server-backed collaboration
import { HocuspocusProvider } from "@hocuspocus/provider";

// Yjs for collaboration
import * as Y from "yjs";

export function createTiptapApi(fetcher: typeof authenticatedFetch = authenticatedFetch) {
  return {
    fetchPreferences: (docId: string) =>
      fetcher(`${API}/projects/${docId}/preferences`),
    fetchDocument: (docId: string) =>
      fetcher(`${API}/documents/${docId}`),
    fetchProject: (projectId: string) =>
      fetcher(`${API}/projects/${projectId}`),
    savePreferences: (docId: string, prefs: Record<string, unknown>) =>
      fetcher(`${API}/projects/${docId}/preferences`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      }),
    fetchRevisions: (docId: string, username: string) =>
      fetcher(`${API}/documents/${docId}/revisions`, {
        headers: { "X-User": username },
      }),
    createRevision: (docId: string, username: string, body: Record<string, unknown>) =>
      fetcher(`${API}/documents/${docId}/revisions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User": username,
        },
        body: JSON.stringify(body),
      }),
    fetchRevision: (docId: string, revisionId: string) =>
      fetcher(`${API}/documents/${docId}/revisions/${revisionId}`),
    fetchArchive: (archiveId: string) => fetcher(`${API}/archive/${archiveId}`),
    fetchTemplates: () => fetcher(`${API}/templates`),
    fetchTemplate: (filename: string) =>
      fetcher(`${API}${buildTemplateUrlPath(filename)}`),
    fetchStarterContent: (docType: string) =>
      fetcher(`/document-types/${encodeURIComponent(docType)}/starter-content`),
  } as const;
}

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
const MenuIcon = dynamic(() => import("lucide-react").then((m) => m.Menu));
const XIcon = dynamic(() => import("lucide-react").then((m) => m.X));
const Loader2 = dynamic(() => import("lucide-react").then((m) => m.Loader2));
const IndentIncrease = dynamic(() =>
  import("lucide-react").then((m) => m.IndentIncrease),
);
const IndentDecrease = dynamic(() =>
  import("lucide-react").then((m) => m.IndentDecrease),
);
const keyboardShortcuts = Extension.create({
  name: "keyboard-shortcuts",
  addKeyboardShortcuts() {
    return {
      "Mod-]": () => {
        runEditorCommand(this.editor, "indent");
        return true;
      },
      "Mod-[": () => {
        runEditorCommand(this.editor, "outdent");
        return true;
      },
      "Mod-Alt-m": () => {
        (this.editor.chain() as any).focus().addComment?.().run?.();
        return true;
      },
      "Mod-Shift-e": () => {
        (this.editor.chain() as any).focus().toggleTrackChanges?.().run?.();
        return true;
      },
    };
  },
});

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
      const res = await authenticatedFetch("/ai/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: selectedText,
        }),
      });
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || "AI rewrite failed");
      }
      const data = await res.json();
      const suggestion = data?.result ?? data?.suggestion;
      if (!suggestion) {
        throw new Error("AI rewrite returned no content");
      }

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
  onStartBlank: () => void;
  templates: any[];
  formattingLocked: boolean;
  activeTemplateLabel: string | null;
  onToggleLint: () => void;
  lintEnabled: boolean;
  lintStatus: ExtensionStatus;
  onToggleCollab: () => void;
  collabEnabled: boolean;
  onToggleAiSuggest: () => void;
  aiSuggestEnabled: boolean;
  onToggleHeadingLock: () => void;
  headingLockEnabled: boolean;
  headingLockStatus: ExtensionStatus;
  onToggleIndentation: () => void;
  indentationEnabled: boolean;
  indentationStatus: ExtensionStatus;
  onToggleSectionNode: () => void;
  sectionNodeEnabled: boolean;
  sectionNodeStatus: ExtensionStatus;
  onToggleMarkReview: () => void;
  markReviewEnabled: boolean;
  markReviewStatus: ExtensionStatus;
  onToggleWatermark: () => void;
  watermarkEnabled: boolean;
  watermarkStatus: ExtensionStatus;
  watermarkText: string;
  onWatermarkText: (text: string) => void;
  suggestions: any[];
  acceptSuggestion: (id: number) => void;
  rejectSuggestion: (id: number) => void;
  clearSuggestions: () => void;
  history: any[];
  onRestore: (id: string) => void;
  onCompare: (id: string) => void;
  validationSummary?: { score?: number; grade?: string; issue_count?: number; source?: string } | null;
}

function Sidebar(props: SidebarProps) {
  const {
    show,
    onClose,
    onTemplateLoad,
    onStartBlank,
    templates,
    formattingLocked,
    activeTemplateLabel,
    onToggleLint,
    lintEnabled,
    lintStatus,
    onToggleCollab,
    collabEnabled,
    onToggleAiSuggest,
    aiSuggestEnabled,
    onToggleHeadingLock,
    headingLockEnabled,
    headingLockStatus,
    onToggleIndentation,
    indentationEnabled,
    indentationStatus,
    onToggleSectionNode,
    sectionNodeEnabled,
    sectionNodeStatus,
    onToggleMarkReview,
    markReviewEnabled,
    markReviewStatus,
    onToggleWatermark,
    watermarkEnabled,
    watermarkStatus,
    watermarkText,
    onWatermarkText,
    suggestions,
    acceptSuggestion,
    rejectSuggestion,
    clearSuggestions,
    history,
    onRestore,
    onCompare,
    validationSummary,
  } = props;

  const extensionItems: ExtensionItem[] = [
    {
      id: "lint",
      label: "Validation (Lint)",
      enabled: lintEnabled,
      status: lintStatus,
      onToggle: onToggleLint,
    },
    {
      id: "heading-lock",
      label: "Heading Lock",
      enabled: headingLockEnabled,
      status: headingLockStatus,
      onToggle: onToggleHeadingLock,
    },
    {
      id: "indentation",
      label: "Indentation",
      enabled: indentationEnabled,
      status: indentationStatus,
      onToggle: onToggleIndentation,
    },
    {
      id: "section-node",
      label: "Section Node",
      enabled: sectionNodeEnabled,
      status: sectionNodeStatus,
      onToggle: onToggleSectionNode,
      seldomUsed: true,
    },
    {
      id: "mark-review",
      label: "Mark Review",
      enabled: markReviewEnabled,
      status: markReviewStatus,
      onToggle: onToggleMarkReview,
      seldomUsed: true,
    },
    {
      id: "watermark",
      label: "Watermark",
      enabled: watermarkEnabled,
      status: watermarkStatus,
      onToggle: onToggleWatermark,
      watermarkText,
      onWatermarkText,
      seldomUsed: true,
    },
  ];
  return (
    <aside
      className={`fixed top-0 right-0 h-full w-80 bg-gray-100 border-l z-50 shadow-lg transform transition-transform duration-200 flex flex-col ${
        show ? "translate-x-0" : "translate-x-full"
      }`}
      style={{ minWidth: "18rem" }}
    >
      <div className="flex-shrink-0 flex justify-between items-center px-4 py-3 border-b bg-white">
        <span className="font-bold text-lg">Tools & Extensions</span>
        <button
          onClick={onClose}
          className="hover:bg-gray-200 rounded p-1"
          aria-label="Close sidebar"
        >
          <XIcon className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-5">
        {/* Templates */}
        <section>
          <div className="font-semibold mb-1">Templates</div>
          <div className="text-xs text-gray-500 mb-2">
            {activeTemplateLabel ? (
              <>
                Active: <span className="font-semibold">{activeTemplateLabel}</span>
                {formattingLocked ? " (formatting locked)" : ""}
              </>
            ) : (
              "Choose a template or start with a blank document."
            )}
          </div>
          <ul className="space-y-1 text-sm">
            <li>
              <button
                className="text-indigo-700 underline"
                onClick={onStartBlank}
              >
                Blank document
              </button>
            </li>
            {templates
              .filter(t => !t.type || t.type === "tiptap" || t.type === "both")
              .map(tpl => (
                <li key={tpl.id || tpl.name}>
                  <button
                    className="text-indigo-700 underline"
                    onClick={() => onTemplateLoad(tpl.id || tpl.name)}
                  >
                    {tpl.label || tpl.name || tpl.id}
                  </button>
                </li>
              ))}
          </ul>
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

        <ExtensionsPanel items={extensionItems} />

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

        {/* Validation Summary */}
        <section>
          <div className="font-semibold mb-1">Validation Summary</div>
          {validationSummary ? (
            <div className="text-sm space-y-1">
              {validationSummary.score != null && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-600">Quality score:</span>
                  <span
                    className={`font-semibold ${
                      validationSummary.score >= 0.8
                        ? "text-green-600"
                        : validationSummary.score >= 0.5
                        ? "text-amber-600"
                        : "text-red-600"
                    }`}
                  >
                    {Math.round(validationSummary.score * 100)}%
                  </span>
                </div>
              )}
              {validationSummary.grade && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-600">Grade level:</span>
                  <span className="font-semibold">{validationSummary.grade}</span>
                </div>
              )}
              {validationSummary.issue_count != null && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-600">Issues found:</span>
                  <span
                    className={`font-semibold ${
                      validationSummary.issue_count === 0 ? "text-green-600" : "text-amber-600"
                    }`}
                  >
                    {validationSummary.issue_count}
                  </span>
                </div>
              )}
              {validationSummary.source && (
                <div className="text-xs text-gray-400">via {validationSummary.source}</div>
              )}
            </div>
          ) : (
            <div className="text-xs text-gray-400">Save the document to run validation.</div>
          )}
        </section>

        {/* History */}
        <section>
          <div className="font-semibold mb-1">History</div>
          <ul className="text-xs text-gray-700 space-y-1">
            {history.map((h: any) => (
              <li key={h.id} className="flex items-center gap-2">
                <button
                  onClick={() => onRestore(h.id)}
                  className="underline"
                >
                  {new Date(h.timestamp).toLocaleString()}
                </button>
                <button
                  onClick={() => onCompare(h.id)}
                  className="underline text-blue-600"
                >
                  Compare
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </aside>
  );
}

export default function TipTapEditorPage({ docId: docIdProp }: { docId?: string }) {
  // Client-side only rendering to prevent SSR issues
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Yjs Setup
  const [collabEnabled, setCollabEnabled] = useState(false);
  const [yDoc, setYDoc] = useState<Y.Doc | null>(null);
  const [provider, setProvider] = useState<any>(null);

  // Lint (validation)
  const [lintEnabled, setLintEnabled] = useState(false);
  const [lintExtension, setLintExtension] = useState<any>(null);
  const [lintStatus, setLintStatus] = useState<ExtensionStatus>("idle");

  // Optional extensions
  const [headingLockEnabled, setHeadingLockEnabled] = useState(false);
  const [headingLockExtension, setHeadingLockExtension] = useState<any>(null);
  const [headingLockStatus, setHeadingLockStatus] = useState<ExtensionStatus>("idle");
  const [indentationEnabled, setIndentationEnabled] = useState(false);
  const [indentationExtension, setIndentationExtension] = useState<any>(null);
  const [indentationStatus, setIndentationStatus] = useState<ExtensionStatus>("idle");
  const [sectionNodeEnabled, setSectionNodeEnabled] = useState(false);
  const [sectionNodeExtension, setSectionNodeExtension] = useState<any>(null);
  const [sectionNodeStatus, setSectionNodeStatus] = useState<ExtensionStatus>("idle");
  const [markReviewEnabled, setMarkReviewEnabled] = useState(false);
  const [markReviewExtension, setMarkReviewExtension] = useState<any>(null);
  const [markReviewStatus, setMarkReviewStatus] = useState<ExtensionStatus>("idle");
  const [watermarkEnabled, setWatermarkEnabled] = useState(false);
  const [watermarkExtension, setWatermarkExtension] = useState<any>(null);
  const [watermarkStatus, setWatermarkStatus] = useState<ExtensionStatus>("idle");
  const [watermarkText, setWatermarkText] = useState("Sample");

  // Submit confirmation modal
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitDone, setSubmitDone] = useState(false);

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [templates, setTemplates] = useState<any[]>([]);
  const [formattingLocked, setFormattingLocked] = useState(false);
  const [activeTemplateLabel, setActiveTemplateLabel] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectDocType, setProjectDocType] = useState<string | null>(null);
  const defaultTemplateApplied = useRef(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const templatePickerRef = useRef<HTMLDivElement>(null);

  const [aiSuggestEnabled, setAiSuggestEnabled] = useState(false);
  interface Suggestion extends NewSuggestion {
    id: number;
  }
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [diffHtml, setDiffHtml] = useState<string | null>(null);

  const api = useMemo(() => createTiptapApi(), []);
  const router = useRouter();
  const docId = (docIdProp ?? router.query.id) as string | undefined;
  const username = useUserStore((s) => s.username) ?? "";
  const [saveStatus, setSaveStatus] = useState<
    "saving" | "saved" | "error" | "offline"
  >("saved");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const saveTimer = useRef<NodeJS.Timeout | null>(null);
  const initialContentLoaded = useRef(false);

  // On-save validation (Item 34 Phase 3)
  interface ValidationSummary {
    score?: number;
    grade?: string;
    issue_count?: number;
    source?: string;
  }
  const [validationSummary, setValidationSummary] = useState<ValidationSummary | null>(null);
  const autoValidationEnabled = useRef(true); // read from backend once on mount
  useEffect(() => {
    authenticatedFetch("/admin/settings/auto-validation")
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d) autoValidationEnabled.current = d.enabled ?? true; })
      .catch(() => {}); // best-effort
  }, []);

  // Offline sync — monitors navigator.onLine and syncs pending drafts on reconnect.
  const { isOnline, pendingCount, syncNow } = useOfflineSync();
  // Stable ref so the HocuspocusProvider callbacks can call syncNow without
  // being stale closures or causing the extensions memo to re-run.
  const syncNowRef = useRef(syncNow);
  useEffect(() => { syncNowRef.current = syncNow; }, [syncNow]);

  // Close template picker when clicking outside
  useEffect(() => {
    if (!showTemplatePicker) return;
    const handler = (e: MouseEvent) => {
      if (templatePickerRef.current && !templatePickerRef.current.contains(e.target as Node)) {
        setShowTemplatePicker(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showTemplatePicker]);

  const persistPreferences = useCallback(
    async (overrides: Partial<Record<string, boolean | string>> = {}) => {
      if (!docId) return;
      const prefs = {
        lint: lintEnabled,
        collab: collabEnabled,
        ai_suggest: aiSuggestEnabled,
        heading_lock: headingLockEnabled,
        indentation: indentationEnabled,
        section_node: sectionNodeEnabled,
        mark_review: markReviewEnabled,
        watermark: watermarkEnabled,
        watermark_text: watermarkText,
        ...overrides,
      };
      try {
        await api.savePreferences(docId, prefs);
      } catch (err) {
        console.error("Failed to save preferences", err);
      }
    },
    [
      api,
      docId,
      lintEnabled,
      collabEnabled,
      aiSuggestEnabled,
      headingLockEnabled,
      indentationEnabled,
      sectionNodeEnabled,
      markReviewEnabled,
      watermarkEnabled,
      watermarkText,
    ],
  );

  useEffect(() => {
    if (!docId) return;
    api.fetchPreferences(docId)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        setLintEnabled(Boolean(data.lint));
        setCollabEnabled(Boolean(data.collab));
        setAiSuggestEnabled(Boolean(data.ai_suggest));
        setHeadingLockEnabled(Boolean(data.heading_lock));
        setIndentationEnabled(Boolean(data.indentation));
        setSectionNodeEnabled(Boolean(data.section_node));
        setMarkReviewEnabled(Boolean(data.mark_review));
        setWatermarkEnabled(Boolean(data.watermark));
        if (typeof data.watermark_text === "string") {
          setWatermarkText(data.watermark_text);
        }
      })
      .catch(() => undefined);
  }, [api, docId]);

  useEffect(() => {
    if (!docId || initialContentLoaded.current) return;
    api.fetchDocument(docId)
      .then((r) => (r.ok ? r.json() : null))
      .then((doc) => {
        if (!doc) return;
        const sanitized = sanitizeHtml(doc.content || "");
        setContent(sanitized && sanitized.trim().length > 0 ? sanitized : "<p></p>");
        if (doc.project && typeof doc.project === "string") {
          setProjectId(doc.project);
        }
        initialContentLoaded.current = true;
      })
      .catch(() => undefined);
  }, [api, docId]);

  useEffect(() => {
    if (!projectId) return;
    api.fetchProject(projectId)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        const docType = data.doc_type || data.docType || data.type;
        if (typeof docType === "string" && docType.trim()) {
          setProjectDocType(docType.trim());
        }
      })
      .catch(() => undefined);
  }, [api, projectId]);

  useEffect(() => {
    if (!docId) return;
    api.fetchRevisions(docId, username)
      .then(res => res.json())
      .then(setHistory)
      .catch(() => {
        if (typeof window !== "undefined") {
          const draft = localStorage.getItem("draft");
          if (draft) setContent(draft);
        }
      });
  }, [api, docId, username]);

  useEffect(() => {
    api.fetchTemplates()
      .then(r => (r.ok ? r.json() : []))
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, [api]);

  const saveRevision = useCallback(
    (html: string, immediate = false, promote = false) => {
      const exec = async () => {
        if (!docId) return;
        if (typeof window !== "undefined") {
          localStorage.setItem("draft", html);
        }
        // Always persist a local draft so content survives connectivity loss.
        saveOfflineDraft(docId, html);
        if (isOffline()) {
          setSaveStatus("offline");
          return;
        }
        setSaveStatus("saving");
        try {
          const body: any = { content: html };
          if (promote) body.promote = true;
          if (yDoc) {
            const update = Y.encodeStateAsUpdate(yDoc);
            body.steps = Array.from(update);
          }
          const res = await api.createRevision(docId, username, body);
          setSaveStatus("saved");
          const data = res.ok ? await res.json() : {};
          if (data.archiveId) {
            const a = await api.fetchArchive(data.archiveId);
            if (a.ok) {
              const rec = await a.json();
              const pdf = rec.metadata?.artefact_locations?.pdf;
              if (pdf) setPdfUrl(pdf);
            }
          }
          const resp = await api.fetchRevisions(docId, username);
          if (resp.ok) {
            setHistory(await resp.json());
          }

          // Item 34 Phase 3: on-save auto-validation (fire-and-forget, non-blocking)
          if (autoValidationEnabled.current) {
            authenticatedFetch("/documents/preflight", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ text: html, document_id: docId }),
            })
              .then((r) => r.ok ? r.json() : null)
              .then((result) => {
                if (!result) return;
                setValidationSummary({
                  score: result.quality_score ?? result.score,
                  grade: result.plain_language_grade ?? result.grade,
                  issue_count: (result.issues ?? result.errors ?? []).length,
                  source: result.source,
                });
              })
              .catch(() => {}); // best-effort — never block save
          }
        } catch (err) {
          const status = await logSaveError(err);
          setSaveStatus(status);
        }
      };
      if (saveTimer.current) clearTimeout(saveTimer.current);
      if (immediate) {
        exec();
      } else {
        saveTimer.current = setTimeout(exec, 500);
      }
    },
    [api, docId, username, yDoc],
  );


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
      keyboardShortcuts,
    ];
    if (lintEnabled && lintExtension) {
      base.push(
        lintExtension.configure({
          rule: {
            match: ({ tr }: { tr: any }) => {
              const issues: any[] = [];
              tr.doc.descendants((node: any, pos: any) => {
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
              tr.doc.descendants((node: any) => {
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
    if (collabEnabled && docId) {
      const cursorUser = {
        name: "You",
        color: "#3b82f6",
      };
      if (!yDoc) {
        const doc = new Y.Doc();
        const hocusProvider = new HocuspocusProvider({
          url: `${API.replace(/^http/, "ws")}/collab`,
          name: docId,
          document: doc,
          onDisconnect() {
            // Server disconnected — subsequent edits will be persisted locally
            // by saveRevision() → saveOfflineDraft() until reconnected.
            setSaveStatus("offline");
          },
          onConnect() {
            // Server reconnected — push any locally pending drafts immediately.
            setSaveStatus("saved");
            syncNowRef.current();
          },
        });
        const awareness = hocusProvider.awareness;
        if (awareness) {
          awareness.setLocalStateField("user", cursorUser);
        }
        setYDoc(doc);
        setProvider(hocusProvider as any);
        base.push(
          Collaboration.configure({ document: doc }),
          CollaborationCursor.configure({
            provider: hocusProvider,
            user: cursorUser,
          }),
        );
      } else if (yDoc && provider) {
        base.push(
          Collaboration.configure({ document: yDoc }),
          CollaborationCursor.configure({
            provider,
            user: cursorUser,
          }),
        );
      }
    }
    if (headingLockEnabled && headingLockExtension) {
      base.push(headingLockExtension());
    }
    if (indentationEnabled && indentationExtension) {
      base.push(indentationExtension());
    }
    if (sectionNodeEnabled && sectionNodeExtension) {
      base.push(sectionNodeExtension());
    }
    if (markReviewEnabled && markReviewExtension) {
      base.push(markReviewExtension());
    }
    if (watermarkEnabled && watermarkExtension) {
      base.push(watermarkExtension(watermarkText));
    }
    base.push(tiptapStructure());
    return base;

  }, [
    lintEnabled,
    lintExtension,
    collabEnabled,
    yDoc,
    provider,
    docId,
    headingLockEnabled,
    headingLockExtension,
    indentationEnabled,
    indentationExtension,
    sectionNodeEnabled,
    sectionNodeExtension,
    markReviewEnabled,
    markReviewExtension,
    watermarkEnabled,
    watermarkExtension,
    watermarkText,
  ]);

  // TipTap Editor
  const [content, setContent] = useState("<p></p>");
  const editor = useEditor(
    {
      extensions,
      content,
      autofocus: true,
      immediatelyRender: false, // Fix SSR hydration warnings
      editorProps: {
        attributes: {
          class:
            "tiptap-content focus:outline-none w-full min-h-[calc(100vh-12rem)]",
        },
      },
      onUpdate: ({ editor }) => {
        const html = editor.getHTML();
        setContent(html);
        saveRevision(html);
      },
      onBlur: ({ editor }) => {
        const html = editor.getHTML();
        setContent(html);
        saveRevision(html, true);
      },
    },
    [extensions],
  );

  useEffect(() => {
    if (editor && editor.getHTML() !== content) {
      editor.commands.setContent(content);
    }
  }, [editor, content]);

  const restoreRevision = useCallback(
    async (id: string) => {
      if (!docId) return;
      try {
        const res = await api.fetchRevision(docId, id);
        if (res.ok) {
          const data = await res.json();
          editor?.commands.setContent(data.content);
        }
      } catch {
        /* ignore */
      }
    },
    [api, docId, editor],
  );

  const compareRevision = useCallback(
    async (id: string) => {
      if (!docId || !editor) return;
      try {
        const res = await api.fetchRevision(docId, id);
        if (res.ok) {
          const data = await res.json();
          const current = editor.getHTML();
          setDiffHtml(generateDiffHtml(data.content, current));
        }
      } catch {
        /* ignore */
      }
    },
    [api, docId, editor],
  );

  const isBlankContent = useCallback((html: string) => {
    const stripped = html
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .replace(/\s+/g, " ")
      .trim();
    return stripped.length === 0;
  }, []);

  function getCurrentBlock(editor: any) {
    if (editor.isActive("heading", { level: 1 })) return "h1";
    if (editor.isActive("heading", { level: 2 })) return "h2";
    if (editor.isActive("heading", { level: 3 })) return "h3";
    return "p";
  }
  function setBlock(editor: any, val: string) {
    if (val === "p") editor.chain().focus().setParagraph().run();
    // Use setHeading (not toggleHeading) so selecting the same level is a
    // no-op rather than toggling back to a paragraph node.
    else if (val === "h1")
      editor.chain().focus().setHeading({ level: 1 }).run();
    else if (val === "h2")
      editor.chain().focus().setHeading({ level: 2 }).run();
    else if (val === "h3")
      editor.chain().focus().setHeading({ level: 3 }).run();
  }

  function handleStartBlank() {
    if (!editor) {
      console.error("Editor not initialized");
      return;
    }
    editor.commands.setContent("<p></p>");
    setContent("<p></p>");
    defaultTemplateApplied.current = true;
    setFormattingLocked(false);
    setActiveTemplateLabel("Blank document");
    setSidebarOpen(false);
  }

  const handleTemplateLoad = useCallback(async (filename: string) => {
    if (!editor) {
      console.error("Editor not initialized");
      return;
    }

    try {
      const res = await api.fetchTemplate(filename);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const sanitized = sanitizeHtml(data.content || "");
      if (!sanitized || sanitized.trim().length === 0) {
        throw new Error("Template content is empty after sanitization");
      }
      editor.commands.setContent(sanitized);
      setContent(sanitized);
      defaultTemplateApplied.current = true;
      const lockFormatting = Boolean(
        data.lockFormatting ??
          data.lock_formatting ??
          data.formatting_lock ??
          data.formattingLocked,
      );
      setFormattingLocked(lockFormatting);
      setActiveTemplateLabel(data.label || data.name || filename);
      setSidebarOpen(false);
    } catch (error) {
      console.error("Template load error:", error);
      console.error("Error details:", {
        filename,
        availableTemplates: templates.map(t => t.id || t.name),
        editorExists: !!editor,
        errorMessage: error instanceof Error ? error.message : "Unknown error",
      });
      toast.error(
        `Failed to load template: ${filename}\n\nError: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }, [api, editor, templates]);

  useEffect(() => {
    if (!editor || defaultTemplateApplied.current) return;
    if (!projectDocType) return;
    if (!isBlankContent(content)) return;

    // Try curated starter-content first; fall back to /templates on 404/error.
    const applyStarterContent = async () => {
      defaultTemplateApplied.current = true; // prevent double-fire while async

      const result = await resolveStarterContent(
        projectDocType,
        (dt) => api.fetchStarterContent(dt),
        sanitizeHtml,
        templates,
      );

      if (result.source === "starter") {
        editor.commands.setContent(result.html);
        setContent(result.html);
        setActiveTemplateLabel(projectDocType);
      } else if (result.source === "template") {
        handleTemplateLoad(result.templateId);
      }
    };

    applyStarterContent();
  }, [api, content, editor, handleTemplateLoad, isBlankContent, projectDocType, templates]);

  function handleToggleLint() {
    if (lintEnabled) {
      setLintEnabled(false);
      setLintExtension(null);
      setLintStatus("idle");
      persistPreferences({ lint: false });
      return;
    }
    setLintStatus("loading");
    import("../../extensions/lint")
      .then((mod) => {
        setLintExtension(() => mod.default);
        setLintEnabled(true);
        setLintStatus("loaded");
        persistPreferences({ lint: true });
      })
      .catch(() => setLintStatus("error"));
  }
  function handleToggleCollab() {
    setCollabEnabled((prev) => {
      const next = !prev;
      if (prev && provider) {
        provider.disconnect();
        setYDoc(null);
        setProvider(null);
      }
      persistPreferences({ collab: next });
      return next;
    });
  }

  function handleToggleAiSuggest() {
    setAiSuggestEnabled((prev) => {
      const next = !prev;
      persistPreferences({ ai_suggest: next });
      return next;
    });
  }

  function handleToggleHeadingLock() {
    if (headingLockEnabled) {
      setHeadingLockEnabled(false);
      setHeadingLockExtension(null);
      setHeadingLockStatus("idle");
      persistPreferences({ heading_lock: false });
      return;
    }
    setHeadingLockStatus("loading");
    import("../../extensions/tiptapHeadingLock")
      .then((mod) => {
        setHeadingLockExtension(() => mod.tiptapHeadingLock);
        setHeadingLockEnabled(true);
        setHeadingLockStatus("loaded");
        persistPreferences({ heading_lock: true });
      })
      .catch(() => setHeadingLockStatus("error"));
  }
  function handleToggleIndentation() {
    if (indentationEnabled) {
      setIndentationEnabled(false);
      setIndentationExtension(null);
      setIndentationStatus("idle");
      persistPreferences({ indentation: false });
      return;
    }
    setIndentationStatus("loading");
    import("../../extensions/tiptapIndentation")
      .then((mod) => {
        setIndentationExtension(() => mod.tiptapIndentation);
        setIndentationEnabled(true);
        setIndentationStatus("loaded");
        persistPreferences({ indentation: true });
      })
      .catch(() => setIndentationStatus("error"));
  }
  function handleToggleSectionNode() {
    if (sectionNodeEnabled) {
      setSectionNodeEnabled(false);
      setSectionNodeExtension(null);
      setSectionNodeStatus("idle");
      persistPreferences({ section_node: false });
      return;
    }
    setSectionNodeStatus("loading");
    import("../../extensions/tiptapSectionNode")
      .then((mod) => {
        setSectionNodeExtension(() => mod.tiptapSectionNode);
        setSectionNodeEnabled(true);
        setSectionNodeStatus("loaded");
        persistPreferences({ section_node: true });
      })
      .catch(() => setSectionNodeStatus("error"));
  }
  function handleToggleMarkReview() {
    if (markReviewEnabled) {
      setMarkReviewEnabled(false);
      setMarkReviewExtension(null);
      setMarkReviewStatus("idle");
      persistPreferences({ mark_review: false });
      return;
    }
    setMarkReviewStatus("loading");
    import("../../extensions/tiptapMarkReview")
      .then((mod) => {
        setMarkReviewExtension(() => mod.tiptapMarkReview);
        setMarkReviewEnabled(true);
        setMarkReviewStatus("loaded");
        persistPreferences({ mark_review: true });
      })
      .catch(() => setMarkReviewStatus("error"));
  }
  function handleToggleWatermark() {
    if (watermarkEnabled) {
      setWatermarkEnabled(false);
      setWatermarkExtension(null);
      setWatermarkStatus("idle");
      persistPreferences({ watermark: false });
      return;
    }
    setWatermarkStatus("loading");
    import("../../extensions/tiptapWatermark")
      .then((mod) => {
        setWatermarkExtension(() => mod.tiptapWatermark);
        setWatermarkEnabled(true);
        setWatermarkStatus("loaded");
        persistPreferences({ watermark: true, watermark_text: watermarkText });
      })
      .catch(() => setWatermarkStatus("error"));
  }

  function handleWatermarkText(text: string) {
    setWatermarkText(text);
    persistPreferences({ watermark_text: text });
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

  if (!isClient || !editor)
    return (
      <div className="flex items-center justify-center h-full">
        Loading TipTap…
      </div>
    );

  return (
    <div className="flex flex-col h-screen w-full bg-white">
      {/* Offline banner — shown when the browser reports no network */}
      {!isOnline && (
        <div className="bg-yellow-100 text-yellow-800 text-center py-2 text-sm font-medium">
          Offline mode — edits are saved locally and will sync when reconnected.
        </div>
      )}
      {/* Syncing banner — shown briefly while pushing pending drafts */}
      {isOnline && pendingCount > 0 && (
        <div className="bg-blue-50 text-blue-700 text-center py-1 text-xs">
          Syncing {pendingCount} pending draft{pendingCount > 1 ? "s" : ""}…
        </div>
      )}
      {/* Header Toolbar */}
      <header className="flex items-center gap-2 bg-gray-100 px-6 py-3 border-b w-full">
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 rounded bg-gray-200 mr-2"
          aria-label="Open sidebar"
          role="button"
        >
          <MenuIcon className="w-5 h-5" />
        </button>
        <span className="text-xl font-bold">TipTap Editor</span>
        {/* Offline badge in toolbar */}
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
          className={`rounded border px-2 py-1 ml-4 ${
            formattingLocked ? "opacity-50 cursor-not-allowed" : ""
          }`}
          aria-label="Block style"
          disabled={formattingLocked}
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
          formattingLocked,
        )}
        {toolbarButton(
          <List className="w-4 h-4" />,
          () => editor.chain().focus().toggleBulletList().run(),
          editor.isActive("bulletList"),
          "Bullet List",
          formattingLocked,
        )}
        {toolbarButton(
          <ListOrdered className="w-4 h-4" />,
          () => editor.chain().focus().toggleOrderedList().run(),
          editor.isActive("orderedList"),
          "Numbered List",
          formattingLocked,
        )}
        {toolbarButton(
          <IndentIncrease className="w-4 h-4" />,
          () => {
            // Try the indentation extension first, then fall back to
            // sinkListItem for list contexts so the button always works
            // on eligible content even when the extension is not loaded.
            if (indentationEnabled && canRunEditorCommand(editor, "indent")) {
              runEditorCommand(editor, "indent");
            } else {
              editor.chain().focus().sinkListItem("listItem").run();
            }
          },
          false,
          "Indent",
          formattingLocked,
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
          false,
          "Outdent",
          formattingLocked,
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
        <InsertMenu
          insertTable={insertTable}
          insertImage={insertImage}
          disabled={formattingLocked}
        />
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
          onClick={() => setShowSubmitModal(true)}
          className="ml-4 px-2 py-1 border rounded bg-indigo-600 text-white hover:bg-indigo-700"
          title="Save a final revision and mark as submitted for review"
        >
          Submit
        </button>
        {/* Submit confirmation modal */}
        {showSubmitModal && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Submit document for review"
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40"
          >
            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 w-96 space-y-4">
              {submitDone ? (
                <>
                  <h2 className="text-base font-semibold text-green-700">Submitted!</h2>
                  <p className="text-sm text-gray-600">
                    Your document has been saved as a new revision and submitted for review.
                    {projectId ? ` Return to the project to track reviewer progress.` : ""}
                  </p>
                  <div className="flex justify-end gap-2">
                    {projectId && (
                      <a
                        href={`/projects/${projectId}`}
                        className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
                      >
                        Go to Project
                      </a>
                    )}
                    <button
                      className="px-3 py-1.5 border rounded text-sm"
                      onClick={() => { setShowSubmitModal(false); setSubmitDone(false); }}
                    >
                      Close
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                    Submit for Review
                  </h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    This will save a final revision of the document and mark it as submitted.
                    Assigned reviewers will be notified.
                  </p>
                  <div className="flex justify-end gap-2">
                    <button
                      className="px-3 py-1.5 border rounded text-sm"
                      onClick={() => setShowSubmitModal(false)}
                    >
                      Cancel
                    </button>
                    <button
                      className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
                      onClick={async () => {
                        await saveRevision(editor.getHTML(), true, true);
                        setSubmitDone(true);
                        toast.success("Document submitted for review.");
                      }}
                    >
                      Confirm Submit
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
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
            Archived • <a href={pdfUrl} className="underline" target="_blank" rel="noopener noreferrer">download PDF</a>
          </div>
        )}
        {/* Item 34 Phase 3: on-save validation quality indicator */}
        {validationSummary && (
          <div
            title={`Quality score: ${validationSummary.score != null ? Math.round(validationSummary.score * 100) : "N/A"}% | Grade: ${validationSummary.grade ?? "N/A"} | Issues: ${validationSummary.issue_count ?? 0}`}
            className={`ml-3 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium cursor-default ${
              (validationSummary.score ?? 0) >= 0.8
                ? "bg-green-100 text-green-800"
                : (validationSummary.score ?? 0) >= 0.5
                ? "bg-amber-100 text-amber-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {validationSummary.score != null
              ? `${Math.round(validationSummary.score * 100)}%`
              : validationSummary.issue_count != null
              ? `${validationSummary.issue_count} issues`
              : "Validated"}
          </div>
        )}
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
      <main className="flex-1 overflow-auto bg-slate-50 px-4 py-6 lg:px-8">
        <div className="mx-auto w-full max-w-[1200px]">
          <EditorContent editor={editor} />
        </div>
      </main>

      {/* Sidebar for templates, validation, collab, history */}
      <Sidebar
        show={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onTemplateLoad={handleTemplateLoad}
        onStartBlank={handleStartBlank}
        templates={templates}
        formattingLocked={formattingLocked}
        activeTemplateLabel={activeTemplateLabel}
        onToggleLint={handleToggleLint}
        lintEnabled={lintEnabled}
        lintStatus={lintStatus}
        onToggleCollab={handleToggleCollab}
        collabEnabled={collabEnabled}
        onToggleAiSuggest={handleToggleAiSuggest}
        aiSuggestEnabled={aiSuggestEnabled}
        onToggleHeadingLock={handleToggleHeadingLock}
        headingLockEnabled={headingLockEnabled}
        headingLockStatus={headingLockStatus}
        onToggleIndentation={handleToggleIndentation}
        indentationEnabled={indentationEnabled}
        indentationStatus={indentationStatus}
        onToggleSectionNode={handleToggleSectionNode}
        sectionNodeEnabled={sectionNodeEnabled}
        sectionNodeStatus={sectionNodeStatus}
        onToggleMarkReview={handleToggleMarkReview}
        markReviewEnabled={markReviewEnabled}
        markReviewStatus={markReviewStatus}
        onToggleWatermark={handleToggleWatermark}
        watermarkEnabled={watermarkEnabled}
        watermarkStatus={watermarkStatus}
        watermarkText={watermarkText}
        onWatermarkText={handleWatermarkText}
        suggestions={suggestions}
        acceptSuggestion={acceptSuggestion}
        rejectSuggestion={rejectSuggestion}
        clearSuggestions={clearSuggestions}
        history={history}
        onRestore={restoreRevision}
        onCompare={compareRevision}
        validationSummary={validationSummary}
      />
      {diffHtml && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-4 rounded max-w-3xl w-full max-h-[80%] overflow-auto">
            <div dangerouslySetInnerHTML={{ __html: diffHtml }} />
            <div className="text-right mt-2">
              <button
                onClick={() => setDiffHtml(null)}
                className="px-2 py-1 border rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

