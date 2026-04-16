import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import sanitizeHtml from "@/utils/sanitize";
import { resolveStarterContent } from "@/lib/starterContent";
import { isBrowser } from "@/lib/browser";
import { createTiptapApi } from "@/lib/tiptapApi";

export interface EditorTemplatesState {
  templates: any[];
  formattingLocked: boolean;
  activeTemplateLabel: string | null;
  projectId: string | null;
  projectDocType: string | null;
  showTemplatePicker: boolean;
  setShowTemplatePicker: React.Dispatch<React.SetStateAction<boolean>>;
  templatePickerRef: React.RefObject<HTMLDivElement | null>;
  handleStartBlank: () => void;
  handleTemplateLoad: (filename: string) => Promise<void>;
}

export function useEditorTemplates({
  docId,
  api,
  editor,
  content,
  setSidebarOpen,
}: {
  docId: string | undefined;
  api: ReturnType<typeof createTiptapApi>;
  editor: any;
  content: string;
  setSidebarOpen: (open: boolean) => void;
}): EditorTemplatesState {
  const [templates, setTemplates] = useState<any[]>([]);
  const [formattingLocked, setFormattingLocked] = useState(false);
  const [activeTemplateLabel, setActiveTemplateLabel] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectDocType, setProjectDocType] = useState<string | null>(null);
  const defaultTemplateApplied = useRef(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const templatePickerRef = useRef<HTMLDivElement | null>(null);
  const pickerListenerRef = useRef<((e: MouseEvent) => void) | null>(null);

  // Load document and extract project ID
  useEffect(() => {
    if (!docId) return;
    api.fetchDocument(docId)
      .then((r) => (r.ok ? r.json() : null))
      .then((doc) => {
        if (!doc) return;
        if (doc.project && typeof doc.project === "string") {
          setProjectId(doc.project);
        }
      })
      .catch(() => undefined);
  }, [api, docId]);

  // Load project doc type
  useEffect(() => {
    if (!projectId) return;
    api.fetchProject(projectId)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        const docType = data.doc_type || data.docType || data.type;
        if (typeof docType === "string" && docType.trim()) {
          setProjectDocType(docType.trim());
        }
      })
      .catch(() => undefined);
  }, [api, projectId]);

  // Load available templates
  useEffect(() => {
    api.fetchTemplates()
      .then((r) => (r.ok ? r.json() : []))
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, [api]);

  // Close template picker when clicking outside
  useEffect(() => {
    if (!showTemplatePicker) {
      if (pickerListenerRef.current) {
        document.removeEventListener("mousedown", pickerListenerRef.current);
        pickerListenerRef.current = null;
      }
      return;
    }
    if (!isBrowser()) return;
    if (pickerListenerRef.current) {
      document.removeEventListener("mousedown", pickerListenerRef.current);
    }
    const handler = (e: MouseEvent) => {
      if (templatePickerRef.current && !templatePickerRef.current.contains(e.target as Node)) {
        setShowTemplatePicker(false);
      }
    };
    pickerListenerRef.current = handler;
    document.addEventListener("mousedown", handler);
    return () => {
      document.removeEventListener("mousedown", handler);
      pickerListenerRef.current = null;
    };
  }, [showTemplatePicker]);

  function handleStartBlank() {
    if (!editor) {
      console.error("Editor not initialized");
      return;
    }
    editor.commands.setContent("<p></p>");
    defaultTemplateApplied.current = true;
    setFormattingLocked(false);
    setActiveTemplateLabel("Blank document");
    setSidebarOpen(false);
  }

  const handleTemplateLoad = useCallback(
    async (filename: string) => {
      if (!editor) {
        console.error("Editor not initialized");
        return;
      }
      try {
        const res = await api.fetchTemplate(filename);
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        const sanitized = sanitizeHtml(data.content || "");
        if (!sanitized || sanitized.trim().length === 0) {
          throw new Error("Template content is empty after sanitization");
        }
        editor.commands.setContent(sanitized);
        defaultTemplateApplied.current = true;
        const lockFormatting = Boolean(
          data.lockFormatting ?? data.lock_formatting ?? data.formatting_lock ?? data.formattingLocked,
        );
        setFormattingLocked(lockFormatting);
        setActiveTemplateLabel(data.label || data.name || filename);
        setSidebarOpen(false);
      } catch (error) {
        console.error("Template load error:", error, { filename, editorExists: !!editor });
        toast.error(
          `Failed to load template: ${filename}\n\nError: ${
            error instanceof Error ? error.message : "Unknown error"
          }`,
        );
      }
    },
    [api, editor, setSidebarOpen],
  );

  // Auto-apply starter content when project doc type is known
  const isBlankContent = useCallback((html: string) => {
    const stripped = html.replace(/<[^>]+>/g, " ").replace(/&nbsp;/gi, " ").replace(/\s+/g, " ").trim();
    return stripped.length === 0;
  }, []);

  useEffect(() => {
    if (!editor || defaultTemplateApplied.current) return;
    if (!projectDocType) return;
    if (!isBlankContent(content)) return;

    const applyStarterContent = async () => {
      defaultTemplateApplied.current = true;
      const result = await resolveStarterContent(
        projectDocType,
        (dt) => api.fetchStarterContent(dt),
        sanitizeHtml,
        templates,
      );
      if (result.source === "starter") {
        editor.commands.setContent(result.html);
        setActiveTemplateLabel(projectDocType);
      } else if (result.source === "template") {
        handleTemplateLoad(result.templateId);
      }
    };

    applyStarterContent();
  }, [api, content, editor, handleTemplateLoad, isBlankContent, projectDocType, templates]);

  return {
    templates,
    formattingLocked,
    activeTemplateLabel,
    projectId,
    projectDocType,
    showTemplatePicker,
    setShowTemplatePicker,
    templatePickerRef,
    handleStartBlank,
    handleTemplateLoad,
  };
}
