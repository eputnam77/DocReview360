import { API, authenticatedFetch } from "@/lib/api";
import { buildTemplateUrlPath } from "@/lib/templatePath";

export function createDocumentEditorApi(
  fetcher: typeof authenticatedFetch = authenticatedFetch,
) {
  return {
    fetchPreferences: (projectId: string) =>
      fetcher(`${API}/projects/${projectId}/preferences`),
    fetchDocument: (docId: string) =>
      fetcher(`${API}/documents/${docId}`),
    fetchProject: (projectId: string) =>
      fetcher(`${API}/projects/${projectId}`),
    listProjectDocuments: (projectId: string) =>
      fetcher(`${API}/documents?project=${encodeURIComponent(projectId)}`),
    savePreferences: (projectId: string, prefs: Record<string, unknown>) =>
      fetcher(`${API}/projects/${projectId}/preferences`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      }),
    fetchRevisions: (docId: string, username: string) =>
      fetcher(`${API}/documents/${docId}/revisions`, {
        headers: { "X-User": username },
      }),
    createRevision: (
      docId: string,
      username: string,
      body: Record<string, unknown>,
    ) =>
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

export const createTiptapApi = createDocumentEditorApi;
