import { useCallback, useEffect, useRef, useState } from "react";
import * as Y from "yjs";
import { authenticatedFetch } from "@/lib/api";
import { logSaveError, isOffline } from "@/utils/saveStatus";
import { saveOfflineDraft } from "@/lib/offlineStorage";
import { writeLocalStorage } from "@/lib/browser";
import { createTiptapApi } from "@/lib/tiptapApi";

export interface ValidationSummary {
  score?: number;
  grade?: string;
  issue_count?: number;
  source?: string;
}

export type SaveStatus = "saving" | "saved" | "error" | "offline";

export interface EditorSaveState {
  saveStatus: SaveStatus;
  pdfUrl: string | null;
  validationSummary: ValidationSummary | null;
  saveRevision: (html: string, immediate?: boolean, promote?: boolean) => void;
  setSaveStatus: React.Dispatch<React.SetStateAction<SaveStatus>>;
}

export function useEditorSave({
  docId,
  username,
  yDoc,
  api,
}: {
  docId: string | undefined;
  username: string;
  yDoc: Y.Doc | null;
  api: ReturnType<typeof createTiptapApi>;
}): EditorSaveState {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [validationSummary, setValidationSummary] = useState<ValidationSummary | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoValidationEnabled = useRef(true);

  // Fetch auto-validation setting once on mount
  useEffect(() => {
    authenticatedFetch("/admin/settings/auto-validation")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) autoValidationEnabled.current = d.enabled ?? true;
      })
      .catch(() => {}); // best-effort
  }, []);

  const saveRevision = useCallback(
    (html: string, immediate = false, promote = false) => {
      const exec = async () => {
        if (!docId) return;
        writeLocalStorage("draft", html);
        saveOfflineDraft(docId, html);

        if (isOffline()) {
          setSaveStatus("offline");
          return;
        }

        setSaveStatus("saving");
        try {
          const body: Record<string, unknown> = { content: html };
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
          // history update is handled by caller via returned setHistory if needed

          // Item 34 Phase 3: on-save auto-validation (fire-and-forget)
          if (autoValidationEnabled.current) {
            authenticatedFetch("/documents/preflight", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ text: html, document_id: docId }),
            })
              .then((r) => (r.ok ? r.json() : null))
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

          // Return the revisions response so caller can update history if needed
          return resp;
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

  return { saveStatus, setSaveStatus, pdfUrl, validationSummary, saveRevision };
}
