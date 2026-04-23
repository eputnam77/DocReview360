import Link from "next/link";
import { useRouter } from "next/router";

import { readBooleanQueryParam, readSingleQueryParam } from "@/lib/editorQuery";
import {
  buildDocumentEditorUrl,
  buildProjectEditorUrl,
} from "@/lib/editorRouting";
import { useProjectDocuments } from "@/lib/useDocuments";

export default function OnlyofficeBackup() {
  const router = useRouter();
  const projectId = readSingleQueryParam(router.query.projectId);
  const explicitDocId =
    readSingleQueryParam(router.query.id) ??
    readSingleQueryParam(router.query.docId);
  const anchor = readSingleQueryParam(router.query.anchor);
  const readonly = readBooleanQueryParam(router.query.readonly);
  const { data: projectDocuments = [], isLoading } = useProjectDocuments(projectId);
  const resolvedDocId = explicitDocId ?? projectDocuments[0]?.id;

  const siblingUrl = (provider: "ckeditor5" | "tiptap") => {
    if (projectId) {
      return buildProjectEditorUrl(provider, projectId, { readonly, anchor });
    }
    return resolvedDocId
      ? buildDocumentEditorUrl(provider, resolvedDocId, { readonly, anchor })
      : "#";
  };

  if (isLoading && !explicitDocId) {
    return <div className="flex h-screen items-center justify-center">Loading document…</div>;
  }

  if (!resolvedDocId) {
    return (
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-4 px-6 py-12">
        <h1 className="text-2xl font-semibold text-gray-900">OnlyOffice backup</h1>
        <p className="text-sm text-gray-600">
          No document is attached to this project yet.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold text-slate-900">
                OnlyOffice backup
              </h1>
              <p className="text-sm text-slate-600">
                This backup route embeds the OnlyOffice handoff page for the selected
                document and stays available during the CKEditor migration.
              </p>
              {anchor && (
                <p className="mt-1 text-xs text-slate-500">
                  Requested jump target: <span className="font-mono">{anchor}</span>
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <Link
                href={siblingUrl("ckeditor5")}
                className="rounded-full border border-slate-200 px-3 py-1 text-slate-700 hover:border-slate-300"
              >
                CKEditor primary
              </Link>
              <Link
                href={siblingUrl("tiptap")}
                className="rounded-full border border-slate-200 px-3 py-1 text-slate-700 hover:border-slate-300"
              >
                TipTap backup
              </Link>
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <iframe
            src={`/onlyoffice/${encodeURIComponent(resolvedDocId)}${readonly ? "?readonly=1" : ""}`}
            title="OnlyOffice backup"
            className="h-[calc(100vh-12rem)] w-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      </div>
    </div>
  );
}
