import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useMemo, useState } from "react";

import ReviewerComments from "@/components/ReviewerComments";
import SubmitModal from "@/components/editor/SubmitModal";
import { createDocumentEditorApi } from "@/lib/documentEditorApi";
import { readBooleanQueryParam, readSingleQueryParam } from "@/lib/editorQuery";
import {
  buildDocumentEditorUrl,
  buildProjectEditorUrl,
} from "@/lib/editorRouting";
import { useProjectDocuments } from "@/lib/useDocuments";
import { useEditorSave } from "@/lib/useEditorSave";
import { useOfflineSync } from "@/lib/useOfflineSync";
import { useUserStore } from "@/state/user";

type RevisionMeta = {
  id: string;
  author?: string;
  timestamp?: string;
};

function ToolbarButton({
  label,
  onClick,
  disabled = false,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="rounded-md border border-slate-200 px-3 py-1 text-sm text-slate-700 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {label}
    </button>
  );
}

export default function TiptapEditorBasic() {
  const router = useRouter();
  const username = useUserStore((state) => state.username) ?? "";
  const api = useMemo(() => createDocumentEditorApi(), []);
  const projectId = readSingleQueryParam(router.query.projectId);
  const explicitDocId =
    readSingleQueryParam(router.query.id) ??
    readSingleQueryParam(router.query.docId);
  const anchor = readSingleQueryParam(router.query.anchor);
  const readonly = readBooleanQueryParam(router.query.readonly);
  const { data: projectDocuments = [], isLoading: projectDocumentsLoading } =
    useProjectDocuments(projectId);
  const resolvedDocId = explicitDocId ?? projectDocuments[0]?.id;
  const [editorData, setEditorData] = useState("<p></p>");
  const [history, setHistory] = useState<RevisionMeta[]>([]);
  const [selectedRevisionId, setSelectedRevisionId] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitDone, setSubmitDone] = useState(false);
  const { isOnline, pendingCount } = useOfflineSync();
  const saveState = useEditorSave({
    docId: resolvedDocId,
    username,
    yDoc: null,
    api,
  });

  const editor = useEditor(
    {
      extensions: [StarterKit],
      editable: !readonly,
      immediatelyRender: false,
      editorProps: {
        attributes: {
          class:
            "tiptap-content min-h-[calc(100vh-18rem)] rounded-xl border border-slate-200 bg-white p-6 focus:outline-none",
        },
      },
      onUpdate: ({ editor: currentEditor }) => {
        if (readonly) {
          return;
        }
        const html = currentEditor.getHTML();
        setEditorData(html);
        saveState.saveRevision(html);
      },
      onBlur: ({ editor: currentEditor }) => {
        if (readonly) {
          return;
        }
        const html = currentEditor.getHTML();
        setEditorData(html);
        saveState.saveRevision(html, true);
      },
    },
    [readonly],
  );

  useEffect(() => {
    if (!resolvedDocId) {
      if (!projectDocumentsLoading) {
        setLoadError(
          projectId
            ? "No document is attached to this project yet."
            : "Document not found.",
        );
      }
      return;
    }

    let cancelled = false;
    setLoadError(null);

    api.fetchDocument(resolvedDocId)
      .then((response) => (response.ok ? response.json() : null))
      .then((document) => {
        if (!document || cancelled) {
          if (!cancelled && !document) {
            setLoadError("Unable to load this document.");
          }
          return;
        }
        const nextData =
          typeof document.content === "string" && document.content.trim().length > 0
            ? document.content
            : "<p></p>";
        setEditorData(nextData);
        editor?.commands.setContent(nextData, false);
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("Unable to load this document.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [api, editor, projectDocumentsLoading, projectId, resolvedDocId]);

  useEffect(() => {
    if (!resolvedDocId) {
      setHistory([]);
      return;
    }
    let cancelled = false;
    api.fetchRevisions(resolvedDocId, username)
      .then((response) => (response.ok ? response.json() : []))
      .then((items) => {
        if (!cancelled) {
          setHistory(Array.isArray(items) ? items : []);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHistory([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [api, resolvedDocId, saveState.saveStatus, submitDone, username]);

  const buildSiblingUrl = useCallback(
    (provider: "ckeditor5" | "onlyoffice") => {
      if (projectId) {
        return buildProjectEditorUrl(provider, projectId, { readonly, anchor });
      }
      return resolvedDocId
        ? buildDocumentEditorUrl(provider, resolvedDocId, { readonly, anchor })
        : "#";
    },
    [anchor, projectId, readonly, resolvedDocId],
  );

  const restoreRevision = useCallback(async () => {
    if (!resolvedDocId || !selectedRevisionId) {
      return;
    }
    const response = await api.fetchRevision(resolvedDocId, selectedRevisionId);
    if (!response.ok) {
      setLoadError("Unable to restore that revision.");
      return;
    }
    const revision = await response.json();
    const nextData =
      typeof revision.content === "string" && revision.content.trim().length > 0
        ? revision.content
        : "<p></p>";
    setEditorData(nextData);
    editor?.commands.setContent(nextData, false);
  }, [api, editor, resolvedDocId, selectedRevisionId]);

  if (projectDocumentsLoading && !explicitDocId) {
    return <div className="flex h-screen items-center justify-center">Loading document…</div>;
  }

  if (!resolvedDocId || loadError || !editor) {
    return (
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-4 px-6 py-12">
        <h1 className="text-2xl font-semibold text-gray-900">TipTap backup</h1>
        <p className="text-sm text-gray-600">{loadError ?? "Document not found."}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {!isOnline && (
        <div className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-800">
          Offline mode: edits are stored locally until the connection returns.
        </div>
      )}
      {isOnline && pendingCount > 0 && (
        <div className="bg-sky-50 px-4 py-2 text-center text-xs text-sky-700">
          Syncing {pendingCount} pending draft{pendingCount === 1 ? "" : "s"}…
        </div>
      )}
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 lg:flex-row">
        <div className="min-w-0 flex-1 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 border-b border-slate-100 pb-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <h1 className="text-xl font-semibold text-slate-900">
                    TipTap backup editor
                  </h1>
                  <p className="text-sm text-slate-600">
                    Reduced-scope TipTap with core formatting only.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-sm">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                    Save status: {saveState.saveStatus}
                  </span>
                  <Link
                    href={buildSiblingUrl("ckeditor5")}
                    className="rounded-full border border-slate-200 px-3 py-1 text-slate-700 hover:border-slate-300"
                  >
                    CKEditor primary
                  </Link>
                  <Link
                    href={buildSiblingUrl("onlyoffice")}
                    className="rounded-full border border-slate-200 px-3 py-1 text-slate-700 hover:border-slate-300"
                  >
                    OnlyOffice backup
                  </Link>
                  {!readonly && (
                    <button
                      className="rounded-full bg-indigo-600 px-3 py-1 text-white hover:bg-indigo-700"
                      onClick={() => setShowSubmitModal(true)}
                      type="button"
                    >
                      Submit for review
                    </button>
                  )}
                </div>
              </div>
              {anchor && (
                <p className="text-xs text-slate-500">
                  Requested jump target: <span className="font-mono">{anchor}</span>
                </p>
              )}
            </div>
            {!readonly && (
              <div className="mt-4 flex flex-wrap gap-2">
                <ToolbarButton
                  label="Bold"
                  onClick={() => editor.chain().focus().toggleBold().run()}
                />
                <ToolbarButton
                  label="Italic"
                  onClick={() => editor.chain().focus().toggleItalic().run()}
                />
                <ToolbarButton
                  label="Bullet list"
                  onClick={() => editor.chain().focus().toggleBulletList().run()}
                />
                <ToolbarButton
                  label="Numbered list"
                  onClick={() => editor.chain().focus().toggleOrderedList().run()}
                />
                <ToolbarButton
                  label="Quote"
                  onClick={() => editor.chain().focus().toggleBlockquote().run()}
                />
                <ToolbarButton
                  label="Undo"
                  onClick={() => editor.chain().focus().undo().run()}
                />
                <ToolbarButton
                  label="Redo"
                  onClick={() => editor.chain().focus().redo().run()}
                />
              </div>
            )}
            <div className="mt-4">
              <EditorContent editor={editor} />
            </div>
          </div>
        </div>

        <aside className="w-full space-y-4 lg:w-[360px]">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Revision history</h2>
            {history.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No revisions yet.</p>
            ) : (
              <div className="mt-3 space-y-3">
                <select
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={selectedRevisionId}
                  onChange={(event) => setSelectedRevisionId(event.target.value)}
                >
                  <option value="">Select a revision</option>
                  {history.map((revision) => (
                    <option key={revision.id} value={revision.id}>
                      {revision.timestamp || revision.id}
                    </option>
                  ))}
                </select>
                <button
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => {
                    void restoreRevision();
                  }}
                  disabled={!selectedRevisionId || readonly}
                  type="button"
                >
                  Restore selected revision
                </button>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Comments</h2>
            <div className="mt-4">
              <ReviewerComments
                docId={resolvedDocId}
                currentUser={username}
                canDispose={!readonly}
              />
            </div>
          </div>
        </aside>
      </div>

      <SubmitModal
        show={showSubmitModal}
        done={submitDone}
        projectId={projectId ?? null}
        onConfirm={async () => {
          saveState.saveRevision(editorData, true, true);
          setSubmitDone(true);
        }}
        onClose={() => {
          setShowSubmitModal(false);
          setSubmitDone(false);
        }}
      />
    </div>
  );
}
