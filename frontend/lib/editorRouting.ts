export type EditorProvider = "ckeditor5" | "tiptap" | "onlyoffice";

export interface EditorRouteOptions {
  readonly?: boolean;
  anchor?: string | null;
}

function buildEditorUrl(
  provider: EditorProvider,
  query: Record<string, string>,
): string {
  const params = new URLSearchParams(query);
  return `/editors/${provider}?${params.toString()}`;
}

export function normalizeEditorProvider(
  value: string | null | undefined,
): EditorProvider {
  const normalized = (value ?? "").trim().toLowerCase();
  if (
    normalized === "ckeditor5" ||
    normalized === "ckeditor" ||
    normalized === "cke5"
  ) {
    return "ckeditor5";
  }
  if (normalized === "onlyoffice") {
    return "onlyoffice";
  }
  if (normalized === "tiptap") {
    return "tiptap";
  }
  return "ckeditor5";
}

export function buildProjectEditorUrl(
  provider: string | null | undefined,
  projectId: string,
  options: EditorRouteOptions = {},
): string {
  const query: Record<string, string> = { projectId };
  if (options.readonly) {
    query.readonly = "1";
  }
  if (options.anchor) {
    query.anchor = options.anchor;
  }
  return buildEditorUrl(normalizeEditorProvider(provider), query);
}

export function buildDocumentEditorUrl(
  provider: string | null | undefined,
  docId: string,
  options: EditorRouteOptions = {},
): string {
  const query: Record<string, string> = { id: docId };
  if (options.readonly) {
    query.readonly = "1";
  }
  if (options.anchor) {
    query.anchor = options.anchor;
  }
  return buildEditorUrl(normalizeEditorProvider(provider), query);
}
