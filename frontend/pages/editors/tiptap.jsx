import { EditorContent, useEditor } from "@tiptap/react";
import { Extension } from "@tiptap/core";
import dynamic from "next/dynamic";
import { useRouter } from "next/router";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { generateDiffHtml } from "../../utils/diff";
import { logSaveError, isOffline } from "@/utils/saveStatus";
import ExtensionsPanel from "../../components/ExtensionsPanel";
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
import { API, authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";
// Custom TipTap extensions
import { tiptapStructure } from "../../extensions/tiptapStructure";
// Hocuspocus provider for server-backed collaboration
import { HocuspocusProvider } from "@hocuspocus/provider";
// Yjs for collaboration
import * as Y from "yjs";
export function createTiptapApi(fetcher = authenticatedFetch) {
    return {
        fetchPreferences: (docId) => fetcher(`${API}/projects/${docId}/preferences`),
        fetchDocument: (docId) => fetcher(`${API}/documents/${docId}`),
        savePreferences: (docId, prefs) => fetcher(`${API}/projects/${docId}/preferences`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(prefs),
        }),
        fetchRevisions: (docId, username) => fetcher(`${API}/documents/${docId}/revisions`, {
            headers: { "X-User": username },
        }),
        createRevision: (docId, username, body) => fetcher(`${API}/documents/${docId}/revisions`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-User": username,
            },
            body: JSON.stringify(body),
        }),
        fetchRevision: (docId, revisionId) => fetcher(`${API}/documents/${docId}/revisions/${revisionId}`),
        fetchArchive: (archiveId) => fetcher(`${API}/archive/${archiveId}`),
        fetchTemplates: () => fetcher(`${API}/templates`),
        fetchTemplate: (filename) => fetcher(`${API}/templates/${filename}`),
    };
}
// Icons
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
const XIcon = dynamic(() => import("lucide-react").then((m) => m.X));
const Loader2 = dynamic(() => import("lucide-react").then((m) => m.Loader2));
const IndentIncrease = dynamic(() => import("lucide-react").then((m) => m.IndentIncrease));
const IndentDecrease = dynamic(() => import("lucide-react").then((m) => m.IndentDecrease));
const keyboardShortcuts = Extension.create({
    name: "keyboard-shortcuts",
    addKeyboardShortcuts() {
        return {
            "Mod-]": () => {
                this.editor.chain().indent?.().run();
                return true;
            },
            "Mod-[": () => {
                this.editor.chain().outdent?.().run();
                return true;
            },
            "Mod-Alt-m": () => {
                this.editor.chain().focus().addComment?.().run();
                return true;
            },
            "Mod-Shift-e": () => {
                this.editor.chain().focus().toggleTrackChanges?.().run();
                return true;
            },
        };
    },
});
function AiSuggestButton({ editor, aiSuggestEnabled, onNewSuggestion, }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    async function handleSuggest() {
        setError(null);
        if (!editor)
            return;
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
            }
            else {
                editor.chain().focus();
                if (empty) {
                    editor.commands.setContent(suggestion);
                }
                else {
                    editor.commands.insertContentAt({ from, to }, suggestion);
                }
            }
        }
        catch (err) {
            setError(err.message || "AI Suggest failed");
        }
        finally {
            setLoading(false);
        }
    }
    return (<span className="ml-2 relative">
      <button onClick={handleSuggest} disabled={loading} className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1" title="AI Suggest (rewrite selection)">
        {loading ? (<Loader2 className="animate-spin w-4 h-4"/>) : (<span>AI Suggest</span>)}
      </button>
      {error && (<div className="absolute left-0 mt-2 bg-red-50 text-red-800 px-2 py-1 text-xs rounded shadow z-50">
          {error}
        </div>)}
    </span>);
}
function Sidebar(props) {
    const { show, onClose, onTemplateLoad, onStartBlank, templates, formattingLocked, activeTemplateLabel, onToggleLint, lintEnabled, lintStatus, onToggleCollab, collabEnabled, onToggleAiSuggest, aiSuggestEnabled, onToggleHeadingLock, headingLockEnabled, headingLockStatus, onToggleIndentation, indentationEnabled, indentationStatus, onToggleSectionNode, sectionNodeEnabled, sectionNodeStatus, onToggleMarkReview, markReviewEnabled, markReviewStatus, onToggleWatermark, watermarkEnabled, watermarkStatus, watermarkText, onWatermarkText, suggestions, acceptSuggestion, rejectSuggestion, clearSuggestions, history, onRestore, onCompare, } = props;
    const extensionItems = [
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
    return (<aside className={`fixed top-0 right-0 h-full w-80 bg-gray-100 border-l z-50 shadow-lg transform transition-transform duration-200 ${show ? "translate-x-0" : "translate-x-full"}`} style={{ minWidth: "18rem" }}>
      <div className="flex justify-between items-center px-4 py-3 border-b bg-white">
        <span className="font-bold text-lg">Tools & Extensions</span>
        <button onClick={onClose} className="hover:bg-gray-200 rounded p-1" aria-label="Close sidebar">
          <XIcon className="w-5 h-5"/>
        </button>
      </div>

      <div className="px-4 py-2 space-y-5">
        {/* Templates */}
        <section>
          <div className="font-semibold mb-1">Templates</div>
          <div className="text-xs text-gray-500 mb-2">
            {activeTemplateLabel ? (<>
                Active: <span className="font-semibold">{activeTemplateLabel}</span>
                {formattingLocked ? " (formatting locked)" : ""}
              </>) : ("Choose a template or start with a blank document.")}
          </div>
          <ul className="space-y-1 text-sm">
            <li>
              <button className="text-indigo-700 underline" onClick={onStartBlank}>
                Blank document
              </button>
            </li>
            {templates
            .filter(t => !t.type || t.type === "tiptap" || t.type === "both")
            .map(tpl => (<li key={tpl.id || tpl.name}>
                  <button className="text-indigo-700 underline" onClick={() => onTemplateLoad(tpl.id || tpl.name)}>
                    {tpl.label || tpl.name || tpl.id}
                  </button>
                </li>))}
          </ul>
        </section>

        {/* AI Suggest */}
        <section>
          <div className="font-semibold mb-1 flex items-center gap-1">
            AI Suggest
            {/* Optional info icon, if you have one */}
            {/* <InfoIcon className="w-4 h-4 text-blue-500" /> */}
          </div>
          <button className={`px-2 py-1 rounded w-full ${aiSuggestEnabled ? "bg-blue-500 text-white" : "bg-gray-200"}`} onClick={onToggleAiSuggest}>
            {aiSuggestEnabled ? "Disable AI Suggest" : "Enable AI Suggest"}
          </button>
          {aiSuggestEnabled && (<div className="mt-2 space-y-2">
              <div className="text-xs text-gray-500 mb-1">
                Select text in the editor and press "AI Suggest" in the toolbar
                to get suggestions.
              </div>
              {suggestions.length === 0 ? (<div className="text-xs text-gray-400">
                  No AI suggestions yet.
                </div>) : (<div className="space-y-2">
                  {suggestions.map((s) => (<div key={s.id} className="border rounded bg-white px-2 py-1 text-sm">
                      <div className="mb-1 text-xs text-gray-600">
                        For: <em>{s.original.slice(0, 40)}...</em>
                      </div>
                      <div className="mb-2">{s.suggestion}</div>
                      <div className="flex gap-2">
                        <button onClick={() => acceptSuggestion(s.id)} className="px-2 py-1 rounded bg-green-500 text-white text-xs">
                          Accept
                        </button>
                        <button onClick={() => rejectSuggestion(s.id)} className="px-2 py-1 rounded bg-red-500 text-white text-xs">
                          Reject
                        </button>
                      </div>
                    </div>))}
                  <button onClick={clearSuggestions} className="mt-2 text-xs underline text-gray-500">
                    Clear all suggestions
                  </button>
                </div>)}
            </div>)}
        </section>

        <ExtensionsPanel items={extensionItems}/>

        {/* Collaboration */}
        <section>
          <div className="font-semibold mb-1">Collaboration</div>
          <button className={`px-2 py-1 rounded w-full ${collabEnabled ? "bg-green-500 text-white" : "bg-gray-200"}`} onClick={onToggleCollab}>
            {collabEnabled ? "Disconnect" : "Connect"}
          </button>
        </section>

        {/* History */}
        <section>
          <div className="font-semibold mb-1">History</div>
          <ul className="text-xs text-gray-700 space-y-1">
            {history.map((h) => (<li key={h.id} className="flex items-center gap-2">
                <button onClick={() => onRestore(h.id)} className="underline">
                  {new Date(h.timestamp).toLocaleString()}
                </button>
                <button onClick={() => onCompare(h.id)} className="underline text-blue-600">
                  Compare
                </button>
              </li>))}
          </ul>
        </section>
      </div>
    </aside>);
}
export default function TipTapEditorPage({ docId: docIdProp }) {
    // Client-side only rendering to prevent SSR issues
    const [isClient, setIsClient] = useState(false);
    useEffect(() => {
        setIsClient(true);
    }, []);
    // Yjs Setup
    const [collabEnabled, setCollabEnabled] = useState(false);
    const [yDoc, setYDoc] = useState(null);
    const [provider, setProvider] = useState(null);
    // Lint (validation)
    const [lintEnabled, setLintEnabled] = useState(false);
    const [lintExtension, setLintExtension] = useState(null);
    const [lintStatus, setLintStatus] = useState("idle");
    // Optional extensions
    const [headingLockEnabled, setHeadingLockEnabled] = useState(false);
    const [headingLockExtension, setHeadingLockExtension] = useState(null);
    const [headingLockStatus, setHeadingLockStatus] = useState("idle");
    const [indentationEnabled, setIndentationEnabled] = useState(false);
    const [indentationExtension, setIndentationExtension] = useState(null);
    const [indentationStatus, setIndentationStatus] = useState("idle");
    const [sectionNodeEnabled, setSectionNodeEnabled] = useState(false);
    const [sectionNodeExtension, setSectionNodeExtension] = useState(null);
    const [sectionNodeStatus, setSectionNodeStatus] = useState("idle");
    const [markReviewEnabled, setMarkReviewEnabled] = useState(false);
    const [markReviewExtension, setMarkReviewExtension] = useState(null);
    const [markReviewStatus, setMarkReviewStatus] = useState("idle");
    const [watermarkEnabled, setWatermarkEnabled] = useState(false);
    const [watermarkExtension, setWatermarkExtension] = useState(null);
    const [watermarkStatus, setWatermarkStatus] = useState("idle");
    const [watermarkText, setWatermarkText] = useState("Sample");
    // Sidebar
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [templates, setTemplates] = useState([]);
    const [formattingLocked, setFormattingLocked] = useState(false);
    const [activeTemplateLabel, setActiveTemplateLabel] = useState(null);
    const [aiSuggestEnabled, setAiSuggestEnabled] = useState(false);
    const [suggestions, setSuggestions] = useState([]);
    const [history, setHistory] = useState([]);
    const [diffHtml, setDiffHtml] = useState(null);
    const api = useMemo(() => createTiptapApi(), []);
    const router = useRouter();
    const docId = (docIdProp ?? router.query.id);
    const username = useUserStore((s) => s.username) ?? "";
    const [saveStatus, setSaveStatus] = useState("saved");
    const [pdfUrl, setPdfUrl] = useState(null);
    const saveTimer = useRef(null);
    const initialContentLoaded = useRef(false);
    const persistPreferences = useCallback(async (overrides = {}) => {
        if (!docId)
            return;
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
        }
        catch (err) {
            console.error("Failed to save preferences", err);
        }
    }, [
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
    ]);
    useEffect(() => {
        if (!docId)
            return;
        api.fetchPreferences(docId)
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
            if (!data)
                return;
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
        if (!docId || initialContentLoaded.current)
            return;
        api.fetchDocument(docId)
            .then((r) => (r.ok ? r.json() : null))
            .then((doc) => {
            if (!doc)
                return;
            const sanitized = sanitizeHtml(doc.content || "");
            setContent(sanitized && sanitized.trim().length > 0 ? sanitized : "<p></p>");
            initialContentLoaded.current = true;
        })
            .catch(() => undefined);
    }, [api, docId]);
    useEffect(() => {
        if (!docId)
            return;
        api.fetchRevisions(docId, username)
            .then(res => res.json())
            .then(setHistory)
            .catch(() => {
            if (typeof window !== "undefined") {
                const draft = localStorage.getItem("draft");
                if (draft)
                    setContent(draft);
            }
        });
    }, [api, docId, username]);
    useEffect(() => {
        api.fetchTemplates()
            .then(r => (r.ok ? r.json() : []))
            .then(setTemplates)
            .catch(() => setTemplates([]));
    }, [api]);
    const saveRevision = useCallback((html, immediate = false, promote = false) => {
        const exec = async () => {
            if (!docId)
                return;
            if (typeof window !== "undefined") {
                localStorage.setItem("draft", html);
            }
            if (isOffline()) {
                setSaveStatus("offline");
                return;
            }
            setSaveStatus("saving");
            try {
                const body = { content: html };
                if (promote)
                    body.promote = true;
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
                        if (pdf)
                            setPdfUrl(pdf);
                    }
                }
                const resp = await api.fetchRevisions(docId, username);
                if (resp.ok) {
                    setHistory(await resp.json());
                }
            }
            catch (err) {
                const status = await logSaveError(err);
                setSaveStatus(status);
            }
        };
        if (saveTimer.current)
            clearTimeout(saveTimer.current);
        if (immediate) {
            exec();
        }
        else {
            saveTimer.current = setTimeout(exec, 500);
        }
    }, [api, docId, username, yDoc]);
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
            base.push(lintExtension.configure({
                rule: {
                    match: ({ tr }) => {
                        const issues = [];
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
                                    message: '"DRAFT" must not appear in the finalized document.',
                                    from: pos + 1 + start,
                                    to: pos + 1 + start + 5,
                                });
                            }
                        });
                        // Rule: Missing "1. Purpose." heading
                        let foundPurpose = false;
                        tr.doc.descendants((node) => {
                            if (node.type.name === "heading" &&
                                /^1\. Purpose\./.test(node.textContent)) {
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
            }));
        }
        if (collabEnabled && docId) {
            if (!yDoc) {
                const doc = new Y.Doc();
                const hocusProvider = new HocuspocusProvider({
                    url: `${API.replace(/^http/, "ws")}/collab`,
                    name: docId,
                    document: doc,
                });
                hocusProvider.awareness.setLocalStateField("user", {
                    name: "You",
                    color: "#3b82f6",
                });
                setYDoc(doc);
                setProvider(hocusProvider);
                base.push(Collaboration.configure({ document: doc }), CollaborationCursor.configure({
                    awareness: hocusProvider.awareness,
                }));
            }
            else if (yDoc && provider) {
                base.push(Collaboration.configure({ document: yDoc }), CollaborationCursor.configure({
                    awareness: provider.awareness,
                }));
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
    const editor = useEditor({
        extensions,
        content,
        autofocus: true,
        immediatelyRender: false, // Fix SSR hydration warnings
        editorProps: {
            attributes: {
                class: "tiptap-content focus:outline-none w-full h-full min-h-[400px] max-w-[860px] mx-auto",
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
    }, [extensions]);
    useEffect(() => {
        if (editor && editor.getHTML() !== content) {
            editor.commands.setContent(content);
        }
    }, [editor, content]);
    const restoreRevision = useCallback(async (id) => {
        if (!docId)
            return;
        try {
            const res = await api.fetchRevision(docId, id);
            if (res.ok) {
                const data = await res.json();
                editor?.commands.setContent(data.content);
            }
        }
        catch {
            /* ignore */
        }
    }, [api, docId, editor]);
    const compareRevision = useCallback(async (id) => {
        if (!docId || !editor)
            return;
        try {
            const res = await api.fetchRevision(docId, id);
            if (res.ok) {
                const data = await res.json();
                const current = editor.getHTML();
                setDiffHtml(generateDiffHtml(data.content, current));
            }
        }
        catch {
            /* ignore */
        }
    }, [api, docId, editor]);
    function getCurrentBlock(editor) {
        if (editor.isActive("heading", { level: 1 }))
            return "h1";
        if (editor.isActive("heading", { level: 2 }))
            return "h2";
        if (editor.isActive("heading", { level: 3 }))
            return "h3";
        return "p";
    }
    function setBlock(editor, val) {
        if (val === "p")
            editor.chain().focus().setParagraph().run();
        else if (val === "h1")
            editor.chain().focus().toggleHeading({ level: 1 }).run();
        else if (val === "h2")
            editor.chain().focus().toggleHeading({ level: 2 }).run();
        else if (val === "h3")
            editor.chain().focus().toggleHeading({ level: 3 }).run();
    }
    function handleStartBlank() {
        if (!editor) {
            console.error("Editor not initialized");
            return;
        }
        editor.commands.setContent("<p></p>");
        setContent("<p></p>");
        setFormattingLocked(false);
        setActiveTemplateLabel("Blank document");
        setSidebarOpen(false);
    }
    async function handleTemplateLoad(filename) {
        if (!editor) {
            console.error("Editor not initialized");
            return;
        }
        try {
            const res = await api.fetchTemplate(filename);
            if (!res.ok)
                throw new Error(await res.text());
            const data = await res.json();
            const sanitized = sanitizeHtml(data.content || "");
            if (!sanitized || sanitized.trim().length === 0) {
                throw new Error("Template content is empty after sanitization");
            }
            editor.commands.setContent(sanitized);
            setContent(sanitized);
            const lockFormatting = Boolean(data.lockFormatting ??
                data.lock_formatting ??
                data.formatting_lock ??
                data.formattingLocked);
            setFormattingLocked(lockFormatting);
            setActiveTemplateLabel(data.label || data.name || filename);
            setSidebarOpen(false);
        }
        catch (error) {
            console.error("Template load error:", error);
            console.error("Error details:", {
                filename,
                availableTemplates: templates.map(t => t.id || t.name),
                editorExists: !!editor,
                errorMessage: error instanceof Error ? error.message : "Unknown error",
            });
            toast.error(`Failed to load template: ${filename}\n\nError: ${error instanceof Error ? error.message : "Unknown error"}`);
        }
    }
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
    function handleWatermarkText(text) {
        setWatermarkText(text);
        persistPreferences({ watermark_text: text });
    }
    function handleNewSuggestion(data) {
        setSuggestions((prev) => [
            ...prev,
            { ...data, id: Date.now() + Math.random() },
        ]);
    }
    function acceptSuggestion(id) {
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
    function rejectSuggestion(id) {
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
        return (<div className="flex items-center justify-center h-full">
        Loading TipTap…
      </div>);
    return (<div className="flex flex-col h-screen w-full bg-white">
      {saveStatus === "offline" && (<div className="bg-yellow-100 text-yellow-800 text-center py-2">
          You are offline. Changes will sync when connection is restored.
        </div>)}
      {/* Header Toolbar */}
      <header className="flex items-center gap-2 bg-gray-100 px-6 py-3 border-b w-full">
        <button onClick={() => setSidebarOpen(true)} className="p-2 rounded bg-gray-200 mr-2" aria-label="Open sidebar" role="button">
          <MenuIcon className="w-5 h-5"/>
        </button>
        <span className="text-xl font-bold">TipTap Editor</span>
        {formattingLocked && (<span className="text-xs text-amber-700 bg-amber-100 px-2 py-1 rounded">
            Template formatting locked
          </span>)}
        <select value={getCurrentBlock(editor)} onChange={(e) => setBlock(editor, e.target.value)} className={`rounded border px-2 py-1 ml-4 ${formattingLocked ? "opacity-50 cursor-not-allowed" : ""}`} aria-label="Block style" disabled={formattingLocked}>
          <option value="p">Paragraph</option>
          <option value="h1">Heading 1</option>
          <option value="h2">Heading 2</option>
          <option value="h3">Heading 3</option>
        </select>
        {toolbarButton(<Bold className="w-4 h-4"/>, () => editor.chain().focus().toggleBold().run(), editor.isActive("bold"), "Bold")}
        {toolbarButton(<Italic className="w-4 h-4"/>, () => editor.chain().focus().toggleItalic().run(), editor.isActive("italic"), "Italic")}
        {toolbarButton(<UnderlineIcon className="w-4 h-4"/>, () => editor.chain().focus().toggleUnderline?.().run(), editor.isActive("underline"), "Underline")}
        {toolbarButton(<Strikethrough className="w-4 h-4"/>, () => editor.chain().focus().toggleStrike().run(), editor.isActive("strike"), "Strikethrough")}
        {toolbarButton(<Code className="w-4 h-4"/>, () => editor.chain().focus().toggleCode().run(), editor.isActive("code"), "Inline Code")}
        {toolbarButton(<Quote className="w-4 h-4"/>, () => editor.chain().focus().toggleBlockquote().run(), editor.isActive("blockquote"), "Blockquote", formattingLocked)}
        {toolbarButton(<List className="w-4 h-4"/>, () => editor.chain().focus().toggleBulletList().run(), editor.isActive("bulletList"), "Bullet List", formattingLocked)}
        {toolbarButton(<ListOrdered className="w-4 h-4"/>, () => editor.chain().focus().toggleOrderedList().run(), editor.isActive("orderedList"), "Numbered List", formattingLocked)}
        {toolbarButton(<IndentIncrease className="w-4 h-4"/>, () => editor.chain().focus().indent().run(), false, "Indent", formattingLocked ||
            !indentationEnabled ||
            !editor.can().chain().focus().indent().run())}
        {toolbarButton(<IndentDecrease className="w-4 h-4"/>, () => editor.chain().focus().outdent().run(), false, "Outdent", formattingLocked ||
            !indentationEnabled ||
            !editor.can().chain().focus().outdent().run())}
        {toolbarButton(<Undo2 className="w-4 h-4"/>, () => editor.chain().focus().undo().run(), false, "Undo")}
        {toolbarButton(<Redo2 className="w-4 h-4"/>, () => editor.chain().focus().redo().run(), false, "Redo")}
        <InsertMenu insertTable={insertTable} insertImage={insertImage} disabled={formattingLocked}/>
        <button onClick={() => saveRevision(editor.getHTML(), true, true)} className="ml-4 px-2 py-1 border rounded">
          Submit
        </button>
        <div className="ml-4 text-sm text-gray-600">
          {saveStatus === "saving"
            ? "Saving…"
            : saveStatus === "saved"
                ? "Saved"
                : saveStatus === "error"
                    ? "Error"
                    : saveStatus === "offline"
                        ? "Offline"
                        : ""}
        </div>
        {pdfUrl && (<div className="ml-4 text-sm text-gray-600">
            Archived • <a href={pdfUrl} className="underline" target="_blank" rel="noopener noreferrer">download PDF</a>
          </div>)}
        <AiSuggestButton editor={editor} aiSuggestEnabled={aiSuggestEnabled} onNewSuggestion={handleNewSuggestion}/>
        <div className="flex-1"/>
      </header>

      {/* Lint (Validation) Overlay */}
      {lintEnabled && (<div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-red-50 border border-red-300 px-6 py-2 rounded z-40 shadow">
          <span className="text-red-600 font-semibold">
            Linting enabled — Issues will be highlighted inline.
          </span>
        </div>)}

      {/* Main Editor */}
      <main className="flex-1 overflow-auto flex justify-center items-start bg-white">
        <div className="w-full max-w-[860px] p-8">
          <EditorContent editor={editor}/>
        </div>
      </main>

      {/* Sidebar for templates, validation, collab, history */}
      <Sidebar show={sidebarOpen} onClose={() => setSidebarOpen(false)} onTemplateLoad={handleTemplateLoad} onStartBlank={handleStartBlank} templates={templates} formattingLocked={formattingLocked} activeTemplateLabel={activeTemplateLabel} onToggleLint={handleToggleLint} lintEnabled={lintEnabled} lintStatus={lintStatus} onToggleCollab={handleToggleCollab} collabEnabled={collabEnabled} onToggleAiSuggest={handleToggleAiSuggest} aiSuggestEnabled={aiSuggestEnabled} onToggleHeadingLock={handleToggleHeadingLock} headingLockEnabled={headingLockEnabled} headingLockStatus={headingLockStatus} onToggleIndentation={handleToggleIndentation} indentationEnabled={indentationEnabled} indentationStatus={indentationStatus} onToggleSectionNode={handleToggleSectionNode} sectionNodeEnabled={sectionNodeEnabled} sectionNodeStatus={sectionNodeStatus} onToggleMarkReview={handleToggleMarkReview} markReviewEnabled={markReviewEnabled} markReviewStatus={markReviewStatus} onToggleWatermark={handleToggleWatermark} watermarkEnabled={watermarkEnabled} watermarkStatus={watermarkStatus} watermarkText={watermarkText} onWatermarkText={handleWatermarkText} suggestions={suggestions} acceptSuggestion={acceptSuggestion} rejectSuggestion={rejectSuggestion} clearSuggestions={clearSuggestions} history={history} onRestore={restoreRevision} onCompare={compareRevision}/>
      {diffHtml && (<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-4 rounded max-w-3xl w-full max-h-[80%] overflow-auto">
            <div dangerouslySetInnerHTML={{ __html: diffHtml }}/>
            <div className="text-right mt-2">
              <button onClick={() => setDiffHtml(null)} className="px-2 py-1 border rounded">
                Close
              </button>
            </div>
          </div>
        </div>)}
    </div>);
}
