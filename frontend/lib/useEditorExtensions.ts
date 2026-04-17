import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as Y from "yjs";
import { HocuspocusProvider } from "@hocuspocus/provider";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import Image from "@tiptap/extension-image";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import { Extension } from "@tiptap/core";
import { API } from "@/lib/api";
import { runEditorCommand } from "@/lib/tiptapCommandUtils";
import { createTiptapApi } from "@/lib/tiptapApi";
import { tiptapStructure } from "@/extensions/tiptapStructure";
import { CommentMark } from "@/extensions/tiptapComments";
import { TrackChanges } from "@/extensions/tiptapTrackChanges";
import SlashCommand from "@/extensions/tiptapSlashCommand";
import type { ExtensionStatus } from "@/components/ExtensionsPanel";
import { useEditorCollab } from "@/lib/useEditorCollab";
import { useEditorLint } from "@/lib/useEditorLint";
import { useEditorOptionalExtensions } from "@/lib/useEditorOptionalExtensions";

export interface EditorExtensionsState {
  // Collab
  collabEnabled: boolean;
  yDoc: Y.Doc | null;
  provider: any;
  // Lint
  lintEnabled: boolean;
  lintStatus: ExtensionStatus;
  // Optional extensions
  headingLockEnabled: boolean;
  headingLockStatus: ExtensionStatus;
  indentationEnabled: boolean;
  indentationStatus: ExtensionStatus;
  sectionNodeEnabled: boolean;
  sectionNodeStatus: ExtensionStatus;
  markReviewEnabled: boolean;
  markReviewStatus: ExtensionStatus;
  watermarkEnabled: boolean;
  watermarkStatus: ExtensionStatus;
  watermarkText: string;
  // Always-on
  commentMarkEnabled: boolean;
  trackChangesEnabled: boolean;
  // Built extension array
  extensions: any[];
  // Handlers
  handleToggleLint: () => void;
  handleToggleCollab: () => void;
  handleToggleAiSuggest: () => void;
  handleToggleHeadingLock: () => void;
  handleToggleIndentation: () => void;
  handleToggleSectionNode: () => void;
  handleToggleMarkReview: () => void;
  handleToggleWatermark: () => void;
  handleWatermarkText: (text: string) => void;
  // AI suggest toggled state lives in main component but is persisted here
  aiSuggestEnabled: boolean;
  setAiSuggestEnabled: React.Dispatch<React.SetStateAction<boolean>>;
}

const keyboardShortcuts = Extension.create({
  name: "keyboard-shortcuts",
  addKeyboardShortcuts() {
    return {
      "Mod-]": () => { runEditorCommand(this.editor, "indent"); return true; },
      "Mod-[": () => { runEditorCommand(this.editor, "outdent"); return true; },
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

export { keyboardShortcuts };

export function useEditorExtensions({
  docId,
  api,
  syncNowRef,
  onSaveStatus,
}: {
  docId: string | undefined;
  api: ReturnType<typeof createTiptapApi>;
  syncNowRef: React.MutableRefObject<() => void>;
  onSaveStatus: (status: "saving" | "saved" | "error" | "offline") => void;
}): EditorExtensionsState {
  const [commentMarkEnabled] = useState(true);
  const [trackChangesEnabled] = useState(true);
  const [aiSuggestEnabled, setAiSuggestEnabled] = useState(false);
  const persistPreferencesRef = useRef<
    (overrides?: Partial<Record<string, boolean | string>>) => Promise<void>
  >(async () => undefined);

  const {
    collabEnabled,
    yDoc,
    provider,
    setCollabEnabled,
    setYDoc,
    setProvider,
    handleToggleCollab,
  } = useEditorCollab({
    persistPreferences: (overrides) => persistPreferencesRef.current(overrides),
  });
  const { lintEnabled, lintExtension, lintStatus, setLintEnabled, handleToggleLint } = useEditorLint({
    persistPreferences: (overrides) => persistPreferencesRef.current(overrides),
  });
  const {
    headingLockEnabled,
    headingLockExtension,
    headingLockStatus,
    setHeadingLockEnabled,
    indentationEnabled,
    indentationExtension,
    indentationStatus,
    setIndentationEnabled,
    sectionNodeEnabled,
    sectionNodeExtension,
    sectionNodeStatus,
    setSectionNodeEnabled,
    markReviewEnabled,
    markReviewExtension,
    markReviewStatus,
    setMarkReviewEnabled,
    watermarkEnabled,
    watermarkExtension,
    watermarkStatus,
    setWatermarkEnabled,
    watermarkText,
    setWatermarkText,
    handleToggleHeadingLock,
    handleToggleIndentation,
    handleToggleSectionNode,
    handleToggleMarkReview,
    handleToggleWatermark,
    handleWatermarkText,
  } = useEditorOptionalExtensions({
    persistPreferences: (overrides) => persistPreferencesRef.current(overrides),
  });

  // ── Preference persistence ─────────────────────────────────────────────────
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
      api, docId, lintEnabled, collabEnabled, aiSuggestEnabled,
      headingLockEnabled, indentationEnabled, sectionNodeEnabled,
      markReviewEnabled, watermarkEnabled, watermarkText,
    ],
  );

  persistPreferencesRef.current = persistPreferences;

  // ── Load preferences on mount ──────────────────────────────────────────────
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

  // ── Toggle handlers ────────────────────────────────────────────────────────
  function handleToggleAiSuggest() {
    setAiSuggestEnabled((prev) => {
      const next = !prev;
      void persistPreferences({ ai_suggest: next });
      return next;
    });
  }

  // ── Extensions memo ────────────────────────────────────────────────────────
  const extensions = useMemo(() => {
    const base: any[] = [
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
                if (node.textContent && node.textContent.includes("DRAFT")) {
                  const start = node.textContent.indexOf("DRAFT");
                  issues.push({
                    message: '"DRAFT" must not appear in the finalized document.',
                    from: pos + 1 + start,
                    to: pos + 1 + start + 5,
                  });
                }
              });
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
      const cursorUser = { name: "You", color: "#3b82f6" };
      if (!yDoc) {
        const doc = new Y.Doc();
        const hocusProvider = new HocuspocusProvider({
          url: `${API.replace(/^http/, "ws")}/collab`,
          name: docId,
          document: doc,
          onDisconnect() {
            onSaveStatus("offline");
          },
          onConnect() {
            onSaveStatus("saved");
            syncNowRef.current();
          },
        });
        if (hocusProvider.awareness) {
          hocusProvider.awareness.setLocalStateField("user", cursorUser);
        }
        setYDoc(doc);
        setProvider(hocusProvider as any);
        base.push(
          Collaboration.configure({ document: doc }),
          CollaborationCursor.configure({ provider: hocusProvider, user: cursorUser }),
        );
      } else if (yDoc && provider) {
        base.push(
          Collaboration.configure({ document: yDoc }),
          CollaborationCursor.configure({ provider, user: cursorUser }),
        );
      }
    }

    if (headingLockEnabled && headingLockExtension) base.push(headingLockExtension());
    if (indentationEnabled && indentationExtension) base.push(indentationExtension());
    if (sectionNodeEnabled && sectionNodeExtension) base.push(sectionNodeExtension());
    if (markReviewEnabled && markReviewExtension) base.push(markReviewExtension());
    if (watermarkEnabled && watermarkExtension) base.push(watermarkExtension(watermarkText));
    if (commentMarkEnabled) base.push(CommentMark as any);
    if (trackChangesEnabled) base.push(TrackChanges as any);
    base.push(tiptapStructure());

    return base;
  }, [
    lintEnabled, lintExtension, collabEnabled, yDoc, provider, docId,
    headingLockEnabled, headingLockExtension, indentationEnabled, indentationExtension,
    sectionNodeEnabled, sectionNodeExtension, markReviewEnabled, markReviewExtension,
    watermarkEnabled, watermarkExtension, watermarkText, commentMarkEnabled, trackChangesEnabled,
    onSaveStatus, syncNowRef,
  ]);

  return {
    collabEnabled, yDoc, provider,
    lintEnabled, lintStatus,
    headingLockEnabled, headingLockStatus,
    indentationEnabled, indentationStatus,
    sectionNodeEnabled, sectionNodeStatus,
    markReviewEnabled, markReviewStatus,
    watermarkEnabled, watermarkStatus, watermarkText,
    commentMarkEnabled, trackChangesEnabled,
    aiSuggestEnabled, setAiSuggestEnabled,
    extensions,
    handleToggleLint, handleToggleCollab, handleToggleAiSuggest,
    handleToggleHeadingLock, handleToggleIndentation, handleToggleSectionNode,
    handleToggleMarkReview, handleToggleWatermark, handleWatermarkText,
  };
}
