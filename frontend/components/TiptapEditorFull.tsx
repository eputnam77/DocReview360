import { EditorContent, useEditor } from "@tiptap/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/router";
import { useOfflineSync } from "@/lib/useOfflineSync";
import { authenticatedFetch } from "@/lib/api";
import { readLocalStorage } from "@/lib/browser";
import { createTiptapApi } from "@/lib/tiptapApi";
import { useUserStore } from "@/state/user";
import { generateDiffHtml } from "@/utils/diff";

import { useEditorExtensions } from "@/lib/useEditorExtensions";
import { useEditorSave } from "@/lib/useEditorSave";
import { useEditorSuggestions } from "@/lib/useEditorSuggestions";
import { useEditorTemplates } from "@/lib/useEditorTemplates";

import EditorSidebar from "./editor/EditorSidebar";
import EditorToolbar from "./editor/EditorToolbar";
import SubmitModal from "./editor/SubmitModal";

export default function TipTapEditorPage({ docId: docIdProp }: { docId?: string }) {
  // Client-side-only guard — prevents SSR/hydration issues with editor DOM
  const [isClient, setIsClient] = useState(false);
  useEffect(() => { setIsClient(true); }, []);

  const [content, setContent] = useState("<p></p>");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitDone, setSubmitDone] = useState(false);
  const [diffHtml, setDiffHtml] = useState<string | null>(null);
  const [history, setHistory] = useState<any[]>([]);

  const api = useMemo(() => createTiptapApi(), []);
  const router = useRouter();
  const docId = (docIdProp ?? router.query.id) as string | undefined;
  const username = useUserStore((s) => s.username) ?? "";

  const { isOnline, pendingCount, syncNow } = useOfflineSync();
  const syncNowRef = useRef(syncNow);
  useEffect(() => { syncNowRef.current = syncNow; }, [syncNow]);

  // ── Core hooks ─────────────────────────────────────────────────────────────
  // Use a ref so extensions can call setSaveStatus before the save hook is returned
  const setSaveStatusRef = useRef<(s: "saving" | "saved" | "error" | "offline") => void>(() => {});
  const ext = useEditorExtensions({
    docId,
    api,
    syncNowRef,
    onSaveStatus: (s) => setSaveStatusRef.current(s),
  });
  const saveWithYDoc = useEditorSave({ docId, username, yDoc: ext.yDoc, api });
  // Wire the ref so future collab callbacks reach the live setter
  setSaveStatusRef.current = saveWithYDoc.setSaveStatus;

  // ── Editor ─────────────────────────────────────────────────────────────────
  const editor = useEditor(
    {
      extensions: ext.extensions,
      content,
      autofocus: true,
      immediatelyRender: false,
      editorProps: {
        attributes: {
          class: "tiptap-content focus:outline-none w-full min-h-[calc(100vh-12rem)]",
        },
      },
      onUpdate: ({ editor }) => {
        const html = editor.getHTML();
        setContent(html);
        saveWithYDoc.saveRevision(html);
      },
      onBlur: ({ editor }) => {
        const html = editor.getHTML();
        setContent(html);
        saveWithYDoc.saveRevision(html, true);
      },
    },
    [ext.extensions],
  );

  // Sync content state → editor when content changes externally (e.g. template load)
  useEffect(() => {
    if (editor && editor.getHTML() !== content) {
      editor.commands.setContent(content);
    }
  }, [editor, content]);

  const suggestions = useEditorSuggestions(editor);

  // ── Template management ────────────────────────────────────────────────────
  const templates = useEditorTemplates({
    docId,
    api,
    editor,
    content,
    setSidebarOpen,
  });

  // ── History: fetch on mount and after saves ────────────────────────────────
  const initialContentLoaded = useRef(false);
  useEffect(() => {
    if (!docId || initialContentLoaded.current) return;
    api.fetchDocument(docId)
      .then((r) => (r.ok ? r.json() : null))
      .then((doc) => {
        if (!doc) return;
        const sanitized = doc.content || "";
        setContent(sanitized && sanitized.trim().length > 0 ? sanitized : "<p></p>");
        initialContentLoaded.current = true;
      })
      .catch(() => undefined);
  }, [api, docId]);

  useEffect(() => {
    if (!docId) return;
    api.fetchRevisions(docId, username)
      .then((res) => res.json())
      .then(setHistory)
      .catch(() => {
        const draft = readLocalStorage("draft");
        if (draft) setContent(draft);
      });
  }, [api, docId, username]);

  // ── Revision management ────────────────────────────────────────────────────
  const restoreRevision = useCallback(
    async (id: string) => {
      if (!docId) return;
      try {
        const res = await api.fetchRevision(docId, id);
        if (res.ok) {
          const data = await res.json();
          editor?.commands.setContent(data.content);
        }
      } catch { /* ignore */ }
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
          setDiffHtml(generateDiffHtml(data.content, editor.getHTML()));
        }
      } catch { /* ignore */ }
    },
    [api, docId, editor],
  );

  // ── Extract inline marks before submit ────────────────────────────────────
  const extractAndPostInlineMarks = useCallback(async () => {
    if (!editor || !templates.projectId) return;
    const { doc } = editor.state;
    const inlineItems: Array<{ text: string; feedback_type: string; range: string }> = [];

    doc.descendants((node, pos) => {
      for (const mark of node.marks) {
        if (mark.type.name === "commentMark") {
          const meta = mark.attrs.metadata ? JSON.parse(mark.attrs.metadata as string) : {};
          inlineItems.push({
            text: meta.text ?? node.textContent ?? "(inline comment)",
            feedback_type: "comment",
            range: `${pos}:${pos + node.nodeSize}`,
          });
        } else if (mark.type.name === "trackInsertion" || mark.type.name === "trackDeletion") {
          const changeType = mark.type.name === "trackInsertion" ? "insertion" : "deletion";
          inlineItems.push({
            text: `Track-change (${changeType}): "${node.textContent}"`,
            feedback_type: "suggestion",
            range: `${pos}:${pos + node.nodeSize}`,
          });
        }
      }
    });

    await Promise.allSettled(
      inlineItems.map((item) =>
        authenticatedFetch(`/projects/${templates.projectId}/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: item.text,
            feedback_type: item.feedback_type,
            source: "inline",
            range_anchor: item.range,
          }),
        }),
      ),
    );
  }, [editor, templates.projectId]);

  function insertTable() {
    editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  }
  function insertImage() {
    const url = prompt("Image URL?");
    if (url) editor?.chain().focus().setImage({ src: url }).run();
  }

  if (!isClient || !editor) {
    return <div className="flex items-center justify-center h-full">Loading TipTap…</div>;
  }

  return (
    <div className="flex flex-col h-screen w-full bg-white">
      {/* Offline / syncing banners */}
      {!isOnline && (
        <div className="bg-yellow-100 text-yellow-800 text-center py-2 text-sm font-medium">
          Offline mode — edits are saved locally and will sync when reconnected.
        </div>
      )}
      {isOnline && pendingCount > 0 && (
        <div className="bg-blue-50 text-blue-700 text-center py-1 text-xs">
          Syncing {pendingCount} pending draft{pendingCount > 1 ? "s" : ""}…
        </div>
      )}

      <EditorToolbar
        editor={editor}
        isOnline={isOnline}
        pendingCount={pendingCount}
        saveStatus={saveWithYDoc.saveStatus}
        pdfUrl={saveWithYDoc.pdfUrl}
        validationSummary={saveWithYDoc.validationSummary}
        docId={docId}
        formattingLocked={templates.formattingLocked}
        showTemplatePicker={templates.showTemplatePicker}
        setShowTemplatePicker={templates.setShowTemplatePicker}
        templatePickerRef={templates.templatePickerRef}
        templates={templates.templates}
        projectDocType={templates.projectDocType}
        handleTemplateLoad={templates.handleTemplateLoad}
        onOpenSidebar={() => setSidebarOpen(true)}
        indentationEnabled={ext.indentationEnabled}
        aiSuggestEnabled={ext.aiSuggestEnabled}
        onNewSuggestion={suggestions.handleNewSuggestion}
        onSubmit={() => setShowSubmitModal(true)}
        insertTable={insertTable}
        insertImage={insertImage}
      />

      <SubmitModal
        show={showSubmitModal}
        done={submitDone}
        projectId={templates.projectId}
        onConfirm={async () => {
          await extractAndPostInlineMarks();
          await saveWithYDoc.saveRevision(editor.getHTML(), true, true);
          setSubmitDone(true);
        }}
        onClose={() => { setShowSubmitModal(false); setSubmitDone(false); }}
      />

      {/* Lint overlay */}
      {ext.lintEnabled && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-red-50 border border-red-300 px-6 py-2 rounded z-40 shadow">
          <span className="text-red-600 font-semibold">
            Linting enabled — Issues will be highlighted inline.
          </span>
        </div>
      )}

      <main className="flex-1 overflow-auto bg-slate-50 px-4 py-6 lg:px-8">
        <div className="mx-auto w-full max-w-[1200px]">
          <EditorContent editor={editor} />
        </div>
      </main>

      <EditorSidebar
        show={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onTemplateLoad={templates.handleTemplateLoad}
        onStartBlank={templates.handleStartBlank}
        templates={templates.templates}
        formattingLocked={templates.formattingLocked}
        activeTemplateLabel={templates.activeTemplateLabel}
        onToggleLint={ext.handleToggleLint}
        lintEnabled={ext.lintEnabled}
        lintStatus={ext.lintStatus}
        onToggleCollab={ext.handleToggleCollab}
        collabEnabled={ext.collabEnabled}
        onToggleAiSuggest={ext.handleToggleAiSuggest}
        aiSuggestEnabled={ext.aiSuggestEnabled}
        onToggleHeadingLock={ext.handleToggleHeadingLock}
        headingLockEnabled={ext.headingLockEnabled}
        headingLockStatus={ext.headingLockStatus}
        onToggleIndentation={ext.handleToggleIndentation}
        indentationEnabled={ext.indentationEnabled}
        indentationStatus={ext.indentationStatus}
        onToggleSectionNode={ext.handleToggleSectionNode}
        sectionNodeEnabled={ext.sectionNodeEnabled}
        sectionNodeStatus={ext.sectionNodeStatus}
        onToggleMarkReview={ext.handleToggleMarkReview}
        markReviewEnabled={ext.markReviewEnabled}
        markReviewStatus={ext.markReviewStatus}
        onToggleWatermark={ext.handleToggleWatermark}
        watermarkEnabled={ext.watermarkEnabled}
        watermarkStatus={ext.watermarkStatus}
        watermarkText={ext.watermarkText}
        onWatermarkText={ext.handleWatermarkText}
        suggestions={suggestions.suggestions}
        acceptSuggestion={suggestions.acceptSuggestion}
        rejectSuggestion={suggestions.rejectSuggestion}
        clearSuggestions={suggestions.clearSuggestions}
        history={history}
        onRestore={restoreRevision}
        onCompare={compareRevision}
        validationSummary={saveWithYDoc.validationSummary}
      />

      {diffHtml && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-4 rounded max-w-3xl w-full max-h-[80%] overflow-auto">
            <div dangerouslySetInnerHTML={{ __html: diffHtml }} />
            <div className="text-right mt-2">
              <button onClick={() => setDiffHtml(null)} className="px-2 py-1 border rounded">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
