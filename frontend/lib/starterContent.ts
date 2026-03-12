/**
 * Starter-content resolution helper.
 *
 * Tries GET /document-types/{docType}/starter-content first; on 404 or
 * network error falls back to a matching entry in the `templates` list.
 * Pure async function — no component state — so it can be unit-tested.
 */

export interface StarterTemplate {
  id?: string;
  name?: string;
  docType?: string;
  doc_type?: string;
  type?: string;
  default?: boolean;
  isDefault?: boolean;
  defaultTemplate?: boolean;
  default_template?: boolean;
}

export type StarterContentResult =
  | { source: "starter"; html: string }
  | { source: "template"; templateId: string }
  | { source: "none" };

/**
 * Resolve starter content for a new blank document.
 *
 * 1. Calls `fetchStarter(docType)` → uses the response HTML when 2xx.
 * 2. Falls back to the best matching entry in `templates` on 404 / error.
 * 3. Returns `{ source: "none" }` when neither source yields usable content.
 */
export async function resolveStarterContent(
  docType: string,
  fetchStarter: (docType: string) => Promise<Response>,
  sanitize: (html: string) => string,
  templates: StarterTemplate[],
): Promise<StarterContentResult> {
  try {
    const res = await fetchStarter(docType);
    if (res.ok) {
      const data = await res.json();
      const html: unknown = data?.content;
      if (html && typeof html === "string" && html.trim().length > 0) {
        const sanitized = sanitize(html);
        if (sanitized && sanitized.trim().length > 0) {
          return { source: "starter", html: sanitized };
        }
      }
    }
  } catch {
    // network error or JSON parse failure — fall through to template fallback
  }

  // Fallback: find a matching template by doc-type, preferring defaults.
  const docTypeKey = docType.trim().toLowerCase();
  const normalize = (value: unknown): string =>
    typeof value === "string" ? value.trim().toLowerCase() : "";

  const findTemplate = (predicate: (t: StarterTemplate) => boolean) =>
    templates.find((t) => {
      try {
        return predicate(t);
      } catch {
        return false;
      }
    });

  const defaultTemplate =
    findTemplate((t) => {
      const dt = normalize(t.docType ?? t.doc_type ?? t.type);
      const isDefault =
        t.default === true ||
        t.isDefault === true ||
        t.defaultTemplate === true ||
        t.default_template === true;
      return !!(dt && dt === docTypeKey && isDefault);
    }) ??
    findTemplate((t) => {
      const dt = normalize(t.docType ?? t.doc_type ?? t.type);
      return !!(dt && dt === docTypeKey);
    });

  if (defaultTemplate) {
    const templateId = defaultTemplate.id ?? defaultTemplate.name;
    if (templateId) {
      return { source: "template", templateId };
    }
  }

  return { source: "none" };
}
