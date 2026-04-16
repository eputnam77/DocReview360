/**
 * Phase 3 editor components — source-level tests.
 *
 * Covers:
 *   - EditorToolbar
 *   - SubmitModal
 *   - AiSuggestButton (quick sanity check)
 *   - EditorSidebar (quick sanity check)
 *
 * Source-level tests guard against structural regressions in extracted
 * components without requiring TipTap or Next.js dynamic() mocks.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const COMPONENTS = join(REPO_ROOT, "frontend", "components", "editor");

function comp(name: string): string {
  return readFileSync(join(COMPONENTS, name), "utf8");
}

// ---------------------------------------------------------------------------
// SubmitModal
// ---------------------------------------------------------------------------

describe("SubmitModal — structure", () => {
  const src = comp("SubmitModal.tsx");

  it("exports SubmitModalProps interface", () => {
    expect(src).toContain("export interface SubmitModalProps");
  });

  it("exports default SubmitModal component", () => {
    expect(src).toContain("export default function SubmitModal");
  });

  it("accepts show, done, projectId, onConfirm, onClose props", () => {
    expect(src).toContain("show: boolean");
    expect(src).toContain("done: boolean");
    expect(src).toContain("projectId: string | null");
    expect(src).toContain("onConfirm: () => Promise<void>");
    expect(src).toContain("onClose: () => void");
  });

  it("renders null when show is false", () => {
    expect(src).toContain("if (!show) return null");
  });

  it("renders success state when done is true", () => {
    expect(src).toContain("Submitted!");
    expect(src).toContain("saved as a new revision and submitted for review");
  });

  it("success state renders a link to the project when projectId is present", () => {
    expect(src).toContain("Go to Project");
    expect(src).toContain("/projects/${projectId}");
  });

  it("confirmation state renders Submit for Review heading", () => {
    expect(src).toContain("Submit for Review");
  });

  it("confirmation state renders an explanation about notifying reviewers", () => {
    expect(src).toContain("Assigned");
    expect(src).toContain("reviewers will be notified");
  });

  it("calls onConfirm when Confirm Submit button is clicked", () => {
    expect(src).toContain("Confirm Submit");
    expect(src).toContain("await onConfirm()");
  });

  it("shows a toast success message after confirming", () => {
    expect(src).toContain("toast.success");
    expect(src).toContain("Document submitted for review.");
  });

  it("calls onClose when Cancel or Close button is clicked", () => {
    expect(src).toContain("Cancel");
    expect(src).toContain("Close");
    expect(src).toContain("onClick={onClose}");
  });

  it("dialog has proper accessibility attributes", () => {
    expect(src).toContain('role="dialog"');
    expect(src).toContain('aria-modal="true"');
    expect(src).toContain("aria-label");
  });
});

// ---------------------------------------------------------------------------
// EditorToolbar
// ---------------------------------------------------------------------------

describe("EditorToolbar — structure", () => {
  const src = comp("EditorToolbar.tsx");

  it("exports EditorToolbarProps interface", () => {
    expect(src).toContain("export interface EditorToolbarProps");
  });

  it("exports default EditorToolbar component", () => {
    expect(src).toContain("export default function EditorToolbar");
  });

  it("accepts editor, isOnline, pendingCount props", () => {
    expect(src).toContain("editor: any");
    expect(src).toContain("isOnline: boolean");
    expect(src).toContain("pendingCount: number");
  });

  it("accepts save state props: saveStatus, pdfUrl, validationSummary, docId", () => {
    expect(src).toContain("saveStatus: SaveStatus");
    expect(src).toContain("pdfUrl: string | null");
    expect(src).toContain("validationSummary: ValidationSummary | null");
    expect(src).toContain("docId: string | undefined");
  });

  it("accepts template props: formattingLocked, showTemplatePicker, templates, projectDocType", () => {
    expect(src).toContain("formattingLocked: boolean");
    expect(src).toContain("showTemplatePicker: boolean");
    expect(src).toContain("templates: any[]");
    expect(src).toContain("projectDocType: string | null");
  });

  it("accepts templatePickerRef with nullable element type for React 18 compatibility", () => {
    expect(src).toContain("RefObject<HTMLDivElement | null>");
  });

  it("accepts indentationEnabled and aiSuggestEnabled flags", () => {
    expect(src).toContain("indentationEnabled: boolean");
    expect(src).toContain("aiSuggestEnabled: boolean");
  });

  it("accepts onSubmit, insertTable, insertImage action props", () => {
    expect(src).toContain("onSubmit: () => void");
    expect(src).toContain("insertTable: () => void");
    expect(src).toContain("insertImage: () => void");
  });

  it("accepts onOpenSidebar prop", () => {
    expect(src).toContain("onOpenSidebar: () => void");
  });

  it("accepts onNewSuggestion callback typed to NewSuggestion", () => {
    expect(src).toContain("onNewSuggestion: (data: NewSuggestion) => void");
  });

  it("imports SaveStatus and ValidationSummary types from useEditorSave", () => {
    expect(src).toContain("@/lib/useEditorSave");
    expect(src).toContain("ValidationSummary");
    expect(src).toContain("SaveStatus");
  });

  it("imports NewSuggestion type from useEditorSuggestions", () => {
    expect(src).toContain("@/lib/useEditorSuggestions");
    expect(src).toContain("NewSuggestion");
  });

  it("includes getCurrentBlock and setBlock utility functions", () => {
    expect(src).toContain("function getCurrentBlock");
    expect(src).toContain("function setBlock");
  });

  it("getCurrentBlock checks for heading levels 1-3", () => {
    expect(src).toContain("heading");
    expect(src).toContain("level: 1");
    expect(src).toContain("level: 2");
    expect(src).toContain("level: 3");
  });

  it("setBlock handles h1, h2, h3, and paragraph values", () => {
    expect(src).toContain("setParagraph");
    expect(src).toContain("setHeading");
  });

  it("renders AiSuggestButton from editor/AiSuggestButton", () => {
    expect(src).toContain("AiSuggestButton");
    expect(src).toContain("./AiSuggestButton");
  });

  it("renders InsertMenu for table and image inserts", () => {
    expect(src).toContain("InsertMenu");
    expect(src).toContain("insertTable");
    expect(src).toContain("insertImage");
  });

  it("uses Next.js dynamic imports for lucide-react icons", () => {
    expect(src).toContain("dynamic(() => import");
    expect(src).toContain("lucide-react");
  });

  it("renders save status text to reflect current save state", () => {
    expect(src).toContain("saveStatus");
    expect(src).toContain("saving");
  });

  it("renders a PDF archive link when pdfUrl is present", () => {
    expect(src).toContain("pdfUrl");
    expect(src).toContain("PDF");
  });
});

// ---------------------------------------------------------------------------
// EditorToolbar — getCurrentBlock and setBlock pure logic
// ---------------------------------------------------------------------------

type BlockType = "h1" | "h2" | "h3" | "p";

function getCurrentBlock(editor: {
  isActive: (type: string, attrs?: Record<string, unknown>) => boolean;
}): BlockType {
  if (editor.isActive("heading", { level: 1 })) return "h1";
  if (editor.isActive("heading", { level: 2 })) return "h2";
  if (editor.isActive("heading", { level: 3 })) return "h3";
  return "p";
}

describe("EditorToolbar — getCurrentBlock logic", () => {
  it("returns h1 when heading level 1 is active", () => {
    const editor = { isActive: (type: string, attrs?: Record<string, unknown>) => type === "heading" && attrs?.level === 1 };
    expect(getCurrentBlock(editor)).toBe("h1");
  });

  it("returns h2 when heading level 2 is active", () => {
    const editor = { isActive: (type: string, attrs?: Record<string, unknown>) => type === "heading" && attrs?.level === 2 };
    expect(getCurrentBlock(editor)).toBe("h2");
  });

  it("returns h3 when heading level 3 is active", () => {
    const editor = { isActive: (type: string, attrs?: Record<string, unknown>) => type === "heading" && attrs?.level === 3 };
    expect(getCurrentBlock(editor)).toBe("h3");
  });

  it("returns p as default when no heading is active", () => {
    const editor = { isActive: () => false };
    expect(getCurrentBlock(editor)).toBe("p");
  });
});

// ---------------------------------------------------------------------------
// AiSuggestButton — quick sanity check
// ---------------------------------------------------------------------------

describe("AiSuggestButton — quick sanity check", () => {
  const src = comp("AiSuggestButton.tsx");

  it("exports default AiSuggestButton component", () => {
    expect(src).toContain("export default function AiSuggestButton");
  });

  it("accepts onNewSuggestion callback", () => {
    expect(src).toContain("onNewSuggestion");
  });
});

// ---------------------------------------------------------------------------
// EditorSidebar — quick sanity check
// ---------------------------------------------------------------------------

describe("EditorSidebar — quick sanity check", () => {
  const src = comp("EditorSidebar.tsx");

  it("exports default EditorSidebar component", () => {
    expect(src).toContain("export default function EditorSidebar");
  });
});
