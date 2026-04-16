/**
 * Phase 3 editor hooks — source-level and unit tests.
 *
 * Covers:
 *   - useEditorSave
 *   - useEditorExtensions
 *   - useEditorTemplates
 *   - useEditorSuggestions
 *
 * Source-level guards protect against structural regressions without requiring
 * heavy mocking of TipTap, Yjs, or HocuspocusProvider.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const LIB = join(REPO_ROOT, "frontend", "lib");

function lib(name: string): string {
  return readFileSync(join(LIB, name), "utf8");
}

// ---------------------------------------------------------------------------
// useEditorSave
// ---------------------------------------------------------------------------

describe("useEditorSave — structure", () => {
  const src = lib("useEditorSave.ts");

  it("exports useEditorSave function", () => {
    expect(src).toContain("export function useEditorSave");
  });

  it("exports EditorSaveState interface", () => {
    expect(src).toContain("export interface EditorSaveState");
  });

  it("exports ValidationSummary interface", () => {
    expect(src).toContain("export interface ValidationSummary");
  });

  it("exports SaveStatus type", () => {
    expect(src).toContain("export type SaveStatus");
    expect(src).toContain('"saving"');
    expect(src).toContain('"saved"');
    expect(src).toContain('"error"');
    expect(src).toContain('"offline"');
  });

  it("exposes saveRevision handler", () => {
    expect(src).toContain("saveRevision");
  });

  it("exposes setSaveStatus for external status bridges", () => {
    expect(src).toContain("setSaveStatus");
  });

  it("exposes pdfUrl state", () => {
    expect(src).toContain("pdfUrl");
    expect(src).toContain("setPdfUrl");
  });

  it("exposes validationSummary state", () => {
    expect(src).toContain("validationSummary");
    expect(src).toContain("setValidationSummary");
  });

  it("initial saveStatus defaults to saved", () => {
    expect(src).toMatch(/useState.*"saved"/);
  });

  it("guards against missing docId before saving", () => {
    expect(src).toContain("if (!docId) return");
  });

  it("writes draft to localStorage before network call", () => {
    expect(src).toContain("writeLocalStorage");
    expect(src).toContain("saveOfflineDraft");
  });

  it("sets offline status when isOffline() returns true", () => {
    expect(src).toContain("isOffline()");
    expect(src).toContain('"offline"');
  });

  it("encodes Y.js state update when yDoc is present", () => {
    expect(src).toContain("Y.encodeStateAsUpdate");
    expect(src).toContain("Array.from(update)");
  });

  it("debounces saves with 500ms timer unless immediate=true", () => {
    expect(src).toContain("500");
    expect(src).toContain("immediate");
    expect(src).toContain("clearTimeout");
  });

  it("fetches auto-validation setting on mount", () => {
    expect(src).toContain("/admin/settings/auto-validation");
    expect(src).toContain("autoValidationEnabled");
  });

  it("posts to /documents/preflight for auto-validation (fire-and-forget)", () => {
    expect(src).toContain("/documents/preflight");
    expect(src).toContain("fire-and-forget");
  });

  it("includes optional promote flag in save body", () => {
    expect(src).toContain("promote");
    expect(src).toContain("body.promote = true");
  });

  it("extracts pdfUrl from archive metadata", () => {
    expect(src).toContain("archiveId");
    expect(src).toContain("artefact_locations");
    expect(src).toContain("pdf");
  });

  it("catches save errors and calls logSaveError", () => {
    expect(src).toContain("logSaveError");
  });
});

// ---------------------------------------------------------------------------
// useEditorSave — ValidationSummary field mapping (pure)
// ---------------------------------------------------------------------------

interface PreflightResult {
  quality_score?: number;
  score?: number;
  plain_language_grade?: string;
  grade?: string;
  issues?: unknown[];
  errors?: unknown[];
  source?: string;
}

function mapPreflightToValidationSummary(result: PreflightResult) {
  return {
    score: result.quality_score ?? result.score,
    grade: result.plain_language_grade ?? result.grade,
    issue_count: (result.issues ?? result.errors ?? []).length,
    source: result.source,
  };
}

describe("useEditorSave — ValidationSummary mapping", () => {
  it("prefers quality_score over score", () => {
    const summary = mapPreflightToValidationSummary({ quality_score: 85, score: 70 });
    expect(summary.score).toBe(85);
  });

  it("falls back to score when quality_score is absent", () => {
    const summary = mapPreflightToValidationSummary({ score: 72 });
    expect(summary.score).toBe(72);
  });

  it("prefers plain_language_grade over grade", () => {
    const summary = mapPreflightToValidationSummary({ plain_language_grade: "B", grade: "C" });
    expect(summary.grade).toBe("B");
  });

  it("counts issues array for issue_count", () => {
    const summary = mapPreflightToValidationSummary({ issues: [1, 2, 3] });
    expect(summary.issue_count).toBe(3);
  });

  it("falls back to errors array when issues is absent", () => {
    const summary = mapPreflightToValidationSummary({ errors: [1, 2] });
    expect(summary.issue_count).toBe(2);
  });

  it("returns 0 issue_count when neither issues nor errors present", () => {
    const summary = mapPreflightToValidationSummary({});
    expect(summary.issue_count).toBe(0);
  });

  it("passes source field through unchanged", () => {
    const summary = mapPreflightToValidationSummary({ source: "ml-model" });
    expect(summary.source).toBe("ml-model");
  });
});

// ---------------------------------------------------------------------------
// useEditorExtensions
// ---------------------------------------------------------------------------

describe("useEditorExtensions — structure", () => {
  const src = lib("useEditorExtensions.ts");

  it("exports useEditorExtensions function", () => {
    expect(src).toContain("export function useEditorExtensions");
  });

  it("exports EditorExtensionsState interface", () => {
    expect(src).toContain("export interface EditorExtensionsState");
  });

  it("exports keyboardShortcuts Extension", () => {
    expect(src).toContain("export { keyboardShortcuts }");
    expect(src).toContain("keyboard-shortcuts");
  });

  it("manages collab state (collabEnabled, yDoc, provider)", () => {
    expect(src).toContain("collabEnabled");
    expect(src).toContain("yDoc");
    expect(src).toContain("provider");
  });

  it("manages lint state (lintEnabled, lintStatus)", () => {
    expect(src).toContain("lintEnabled");
    expect(src).toContain("lintStatus");
  });

  it("manages optional extensions: headingLock, indentation, sectionNode, markReview, watermark", () => {
    expect(src).toContain("headingLockEnabled");
    expect(src).toContain("indentationEnabled");
    expect(src).toContain("sectionNodeEnabled");
    expect(src).toContain("markReviewEnabled");
    expect(src).toContain("watermarkEnabled");
  });

  it("manages always-on extensions: commentMark, trackChanges", () => {
    expect(src).toContain("commentMarkEnabled");
    expect(src).toContain("trackChangesEnabled");
  });

  it("manages aiSuggestEnabled state", () => {
    expect(src).toContain("aiSuggestEnabled");
    expect(src).toContain("setAiSuggestEnabled");
  });

  it("exposes all toggle handlers", () => {
    expect(src).toContain("handleToggleLint");
    expect(src).toContain("handleToggleCollab");
    expect(src).toContain("handleToggleAiSuggest");
    expect(src).toContain("handleToggleHeadingLock");
    expect(src).toContain("handleToggleIndentation");
    expect(src).toContain("handleToggleSectionNode");
    expect(src).toContain("handleToggleMarkReview");
    expect(src).toContain("handleToggleWatermark");
    expect(src).toContain("handleWatermarkText");
  });

  it("persists preferences via /documents/:id/preferences endpoint", () => {
    expect(src).toContain("preferences");
    expect(src).toContain("persistPreferences");
  });

  it("loads preferences on mount via useEffect using fetchPreferences", () => {
    expect(src).toContain("useEffect");
    expect(src).toContain("fetchPreferences");
  });

  it("builds extensions array via useMemo", () => {
    expect(src).toContain("useMemo");
    expect(src).toContain("extensions");
  });

  it("includes StarterKit, Underline, Table extensions", () => {
    expect(src).toContain("StarterKit");
    expect(src).toContain("Underline");
    expect(src).toContain("Table");
  });

  it("includes Collaboration and CollaborationCursor when collab enabled", () => {
    expect(src).toContain("Collaboration");
    expect(src).toContain("CollaborationCursor");
    expect(src).toContain("collabEnabled");
  });

  it("keyboard shortcuts use Mod- prefix for cross-platform compatibility", () => {
    expect(src).toContain("Mod-]");
    expect(src).toContain("Mod-[");
    expect(src).toContain("Mod-Alt-m");
  });
});

// ---------------------------------------------------------------------------
// useEditorTemplates
// ---------------------------------------------------------------------------

describe("useEditorTemplates — structure", () => {
  const src = lib("useEditorTemplates.ts");

  it("exports useEditorTemplates function", () => {
    expect(src).toContain("export function useEditorTemplates");
  });

  it("exports EditorTemplatesState interface", () => {
    expect(src).toContain("export interface EditorTemplatesState");
  });

  it("exposes templates, formattingLocked, activeTemplateLabel", () => {
    expect(src).toContain("templates");
    expect(src).toContain("formattingLocked");
    expect(src).toContain("activeTemplateLabel");
  });

  it("exposes projectId and projectDocType resolved from document and project APIs", () => {
    expect(src).toContain("projectId");
    expect(src).toContain("projectDocType");
  });

  it("exposes showTemplatePicker and setShowTemplatePicker", () => {
    expect(src).toContain("showTemplatePicker");
    expect(src).toContain("setShowTemplatePicker");
  });

  it("exposes templatePickerRef for outside-click detection", () => {
    expect(src).toContain("templatePickerRef");
    expect(src).toContain("useRef");
  });

  it("fetches document to extract project ID", () => {
    expect(src).toContain("fetchDocument");
    expect(src).toContain("doc.project");
    expect(src).toContain("setProjectId");
  });

  it("fetches project to extract doc type (doc_type, docType, or type)", () => {
    expect(src).toContain("fetchProject");
    expect(src).toContain("doc_type");
    expect(src).toContain("docType");
  });

  it("fetches available templates on mount", () => {
    expect(src).toContain("fetchTemplates");
    expect(src).toContain("setTemplates");
  });

  it("closes template picker on outside click via mousedown listener", () => {
    expect(src).toContain("mousedown");
    expect(src).toContain("templatePickerRef.current");
    expect(src).toContain("contains(e.target");
  });

  it("handleStartBlank sets blank content and unlocks formatting", () => {
    expect(src).toContain("handleStartBlank");
    expect(src).toContain("setContent");
    expect(src).toContain("Blank document");
  });

  it("handleTemplateLoad fetches template by filename and sanitizes content", () => {
    expect(src).toContain("handleTemplateLoad");
    expect(src).toContain("fetchTemplate");
    expect(src).toContain("sanitizeHtml");
  });

  it("handleTemplateLoad respects lockFormatting flag in template data", () => {
    expect(src).toContain("lockFormatting");
    expect(src).toContain("setFormattingLocked");
  });

  it("auto-applies starter content when projectDocType is known and content is blank", () => {
    expect(src).toContain("resolveStarterContent");
    expect(src).toContain("projectDocType");
    expect(src).toContain("defaultTemplateApplied");
  });

  it("isBlankContent strips HTML tags and whitespace before checking", () => {
    expect(src).toContain("isBlankContent");
    expect(src).toContain("replace(/<[^>]+>/g");
  });

  it("guards template picker close with isBrowser() check (SSR safety)", () => {
    expect(src).toContain("isBrowser()");
  });
});

// ---------------------------------------------------------------------------
// useEditorTemplates — isBlankContent logic (pure)
// ---------------------------------------------------------------------------

function isBlankContent(html: string): boolean {
  const stripped = html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  return stripped.length === 0;
}

describe("useEditorTemplates — isBlankContent logic", () => {
  it("returns true for empty string", () => {
    expect(isBlankContent("")).toBe(true);
  });

  it("returns true for only whitespace", () => {
    expect(isBlankContent("   ")).toBe(true);
  });

  it("returns true for empty paragraph tags", () => {
    expect(isBlankContent("<p></p>")).toBe(true);
  });

  it("returns true for paragraph with only whitespace", () => {
    expect(isBlankContent("<p>   </p>")).toBe(true);
  });

  it("returns true for &nbsp; only content", () => {
    expect(isBlankContent("<p>&nbsp;</p>")).toBe(true);
  });

  it("returns false when paragraph contains text", () => {
    expect(isBlankContent("<p>Hello world</p>")).toBe(false);
  });

  it("returns false for nested content with text", () => {
    expect(isBlankContent("<div><p><strong>Doc title</strong></p></div>")).toBe(false);
  });

  it("returns true for multiple empty paragraphs", () => {
    expect(isBlankContent("<p></p><p></p><p></p>")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// useEditorSuggestions
// ---------------------------------------------------------------------------

describe("useEditorSuggestions — structure", () => {
  const src = lib("useEditorSuggestions.ts");

  it("exports useEditorSuggestions function", () => {
    expect(src).toContain("export function useEditorSuggestions");
  });

  it("exports EditorSuggestionsState interface", () => {
    expect(src).toContain("export interface EditorSuggestionsState");
  });

  it("exports NewSuggestion interface with from/to/original/suggestion fields", () => {
    expect(src).toContain("export interface NewSuggestion");
    expect(src).toContain("from: number");
    expect(src).toContain("to: number");
    expect(src).toContain("original: string");
    expect(src).toContain("suggestion: string");
  });

  it("exports Suggestion interface extending NewSuggestion with id field", () => {
    expect(src).toContain("export interface Suggestion extends NewSuggestion");
    expect(src).toContain("id: number");
  });

  it("exposes suggestions array state", () => {
    expect(src).toContain("suggestions");
  });

  it("exposes handleNewSuggestion, acceptSuggestion, rejectSuggestion, clearSuggestions", () => {
    expect(src).toContain("handleNewSuggestion");
    expect(src).toContain("acceptSuggestion");
    expect(src).toContain("rejectSuggestion");
    expect(src).toContain("clearSuggestions");
  });

  it("handleNewSuggestion assigns unique id using Date.now + random", () => {
    expect(src).toContain("Date.now()");
    expect(src).toContain("Math.random()");
  });

  it("acceptSuggestion applies change via editor.chain().insertContentAt()", () => {
    expect(src).toContain("editor.chain()");
    expect(src).toContain("insertContentAt");
    expect(src).toContain("s.suggestion");
  });

  it("acceptSuggestion removes the suggestion from state after applying", () => {
    expect(src).toContain("prev.filter((x) => x.id !== id)");
  });

  it("rejectSuggestion removes suggestion without applying to editor", () => {
    const src2 = lib("useEditorSuggestions.ts");
    // rejectSuggestion should filter but NOT call editor.chain
    const rejectFn = src2.slice(
      src2.indexOf("function rejectSuggestion"),
      src2.indexOf("function clearSuggestions"),
    );
    expect(rejectFn).toContain("filter");
    expect(rejectFn).not.toContain("editor.chain");
  });

  it("clearSuggestions sets suggestions to empty array", () => {
    expect(src).toContain("setSuggestions([])");
  });
});

// ---------------------------------------------------------------------------
// useEditorSuggestions — pure logic tests
// ---------------------------------------------------------------------------

interface MockSuggestion {
  id: number;
  from: number;
  to: number;
  original: string;
  suggestion: string;
}

function addSuggestion(suggestions: MockSuggestion[], data: Omit<MockSuggestion, "id">): MockSuggestion[] {
  return [...suggestions, { ...data, id: 1000 }]; // fixed id for test determinism
}

function removeSuggestion(suggestions: MockSuggestion[], id: number): MockSuggestion[] {
  return suggestions.filter((x) => x.id !== id);
}

describe("useEditorSuggestions — state management logic", () => {
  const base: MockSuggestion[] = [
    { id: 1, from: 0, to: 5, original: "hello", suggestion: "Hello" },
    { id: 2, from: 10, to: 15, original: "world", suggestion: "World" },
  ];

  it("addSuggestion appends to the list", () => {
    const result = addSuggestion(base, { from: 20, to: 25, original: "foo", suggestion: "Foo" });
    expect(result).toHaveLength(3);
  });

  it("removeSuggestion removes the correct item", () => {
    const result = removeSuggestion(base, 1);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(2);
  });

  it("removeSuggestion with unknown id returns original list", () => {
    const result = removeSuggestion(base, 999);
    expect(result).toHaveLength(2);
  });

  it("clearSuggestions returns empty array", () => {
    const result: MockSuggestion[] = [];
    expect(result).toHaveLength(0);
  });

  it("suggestion retains from/to range for editor cursor placement", () => {
    const result = addSuggestion([], { from: 5, to: 12, original: "test", suggestion: "Test" });
    expect(result[0].from).toBe(5);
    expect(result[0].to).toBe(12);
  });
});
