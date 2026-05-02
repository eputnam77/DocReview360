import { CKEditor } from "@ckeditor/ckeditor5-react";
import {
  BlockQuote,
  Bold,
  ClassicEditor,
  Essentials,
  Heading,
  Italic,
  Link as CKLink,
  List,
  Paragraph,
  Table,
  TableToolbar,
  Underline,
} from "ckeditor5";
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
import { resolveStarterContent } from "@/lib/starterContent";
import { useProjectDocuments } from "@/lib/useDocuments";
import { useEditorSave } from "@/lib/useEditorSave";
import { useOfflineSync } from "@/lib/useOfflineSync";
import { useUserStore } from "@/state/user";
import sanitizeHtml from "@/utils/sanitize";

type RevisionMeta = {
  id: string;
  author?: string;
  timestamp?: string;
};

export const CKEDITOR_CONFIG: Record<string, unknown> = {
  licenseKey: "GPL",
  plugins: [
    Essentials,
    Paragraph,
    Bold,
    Italic,
    Underline,
    Heading,
    List,
    CKLink,
    BlockQuote,
    Table,
    TableToolbar,
  ],
  toolbar: [
    "undo",
    "redo",
    "|",
    "heading",
    "|",
    "bold",
    "italic",
    "underline",
    "|",
    "link",
    "bulletedList",
    "numberedList",
    "blockQuote",
    "insertTable",
  ],
  table: {
    contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"],
  },
};

type EditorDocumentPayload = {
  content?: unknown;
  version_number?: unknown;
  history?: unknown[];
  project?: unknown;
  doc_type?: unknown;
  docType?: unknown;
  type?: unknown;
};

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

export function isBlankEditorContent(html: string): boolean {
  const stripped = html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  return stripped.length === 0;
}

function formatTimestamp(value?: string): string {
  if (!value) {
    return "Unknown time";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString();
}

export default function CKEditorPrimary() {
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
  const [editorVersionKey, setEditorVersionKey] = useState("empty");
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

  useEffect(() => {
    if (!resolvedDocId) {
      if (!projectDocumentsLoading && router.isReady) {
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
      .then(async (document: EditorDocumentPayload | null) => {
        if (!document || cancelled) {
          if (!cancelled && !document) {
            setLoadError("Unable to load this document.");
          }
          return;
        }
        let nextData =
          typeof document.content === "string" && document.content.trim().length > 0
            ? document.content
            : "<p></p>";
        let contentSource = "document";
        const sourceProjectId = projectId ?? readString(document.project);
        if (isBlankEditorContent(nextData) && sourceProjectId) {
          try {
            const projectResponse = await api.fetchProject(sourceProjectId);
            const project = projectResponse.ok ? await projectResponse.json() : null;
            const docType =
              readString(project?.doc_type) ??
              readString(project?.docType) ??
              readString(project?.type) ??
              readString(document.doc_type) ??
              readString(document.docType) ??
              readString(document.type);
            if (docType) {
              const templatesResponse = await api.fetchTemplates();
              const templates = templatesResponse.ok ? await templatesResponse.json() : [];
              const starter = await resolveStarterContent(
                docType,
                (dt) => api.fetchStarterContent(dt),
                sanitizeHtml,
                Array.isArray(templates) ? templates : [],
              );
              if (starter.source === "starter") {
                nextData = starter.html;
                contentSource = "starter";
              } else if (starter.source === "template") {
                const templateResponse = await api.fetchTemplate(starter.templateId);
                if (templateResponse.ok) {
                  const template = await templateResponse.json();
                  const sanitized = sanitizeHtml(template?.content || "");
                  if (sanitized.trim().length > 0) {
                    nextData = sanitized;
                    contentSource = `template:${starter.templateId}`;
                  }
                }
              }
            }
          } catch {
            nextData = "<p></p>";
          }
        }
        if (cancelled) {
          return;
        }
        setEditorData(nextData);
        setEditorVersionKey(
          `${resolvedDocId}:${document.version_number ?? document.history?.length ?? "current"}:${contentSource}`,
        );
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("Unable to load this document.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [api, projectDocumentsLoading, projectId, resolvedDocId, router.isReady]);

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

  const buildBackupUrl = useCallback(
    (provider: "tiptap" | "onlyoffice") => {
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
    setEditorVersionKey(`${resolvedDocId}:revision:${selectedRevisionId}`);
  }, [api, resolvedDocId, selectedRevisionId]);

  if (projectDocumentsLoading && !explicitDocId) {
    return <div className="flex h-screen items-center justify-center">Loading document…</div>;
  }

  if (!resolvedDocId || loadError) {
    return (
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-4 px-6 py-12">
        <h1 className="text-2xl font-semibold text-gray-900">CKEditor 5</h1>
        <p className="text-sm text-gray-600">{loadError ?? "Document not found."}</p>
        {projectId && (
          <Link
            href={`/projects/${projectId}`}
            className="text-sm font-medium text-indigo-600 hover:underline"
          >
            Return to project
          </Link>
        )}
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
            <div className="flex flex-col gap-3 border-b border-slate-100 pb-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1">
                <h1 className="text-xl font-semibold text-slate-900">
                  Project Editor
                </h1>
                <p className="text-sm text-slate-600">
                  CKEditor 5 is the primary editing path for project reviews.
                </p>
                {anchor && (
                  <p className="text-xs text-slate-500">
                    Requested jump target: <span className="font-mono">{anchor}</span>
                  </p>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                  Save status: {saveState.saveStatus}
                </span>
                <Link
                  href={buildBackupUrl("tiptap")}
                  className="rounded-full border border-slate-200 px-3 py-1 text-slate-700 hover:border-slate-300"
                >
                  TipTap backup
                </Link>
                <Link
                  href={buildBackupUrl("onlyoffice")}
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
            <div className="mt-4 rounded-xl border border-slate-200 bg-white p-2">
              <CKEditor
                key={editorVersionKey}
                editor={ClassicEditor}
                config={CKEDITOR_CONFIG}
                data={editorData}
                disabled={readonly}
                onChange={(_event, editor) => {
                  if (readonly) {
                    return;
                  }
                  const html = editor.getData();
                  setEditorData(html);
                  saveState.saveRevision(html);
                }}
                onBlur={(_event, editor) => {
                  if (readonly) {
                    return;
                  }
                  const html = editor.getData();
                  setEditorData(html);
                  saveState.saveRevision(html, true);
                }}
              />
            </div>
          </div>
        </div>

        <aside className="w-full space-y-4 lg:w-[360px]">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Revision history</h2>
            <p className="mt-1 text-xs text-slate-500">
              Autosave writes revisions through the existing document API.
            </p>
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
                      {formatTimestamp(revision.timestamp)} · {revision.author || "unknown"}
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
            <p className="mt-1 text-xs text-slate-500">
              Review comments stay on the shared document record during migration.
            </p>
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
