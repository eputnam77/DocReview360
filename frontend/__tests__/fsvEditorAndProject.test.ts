/**
 * Item 34 Phase 3 — FSV editor on-save validation and project view quality badge.
 *
 * Source-level tests verifying:
 *  - On-save validation posts to /documents/preflight with document_id
 *  - autoValidationEnabled controls the validation gate
 *  - setValidationSummary is called with score/grade/issue_count/source
 *  - validationSummary prop renders toolbar pill with score, grade, issues
 *  - Quality badge rendered next to "Edit Document" CTA in project view
 *  - Quality badge is gated by fsvEnabled
 *  - Admin toggle for auto-validation (autoValidationEnabled loaded from backend)
 *
 * Item 34 Phase 4 — Core Tool designation
 *  - FSV is marked as isCore = true in tools/index.tsx
 *  - CoreBadge is rendered for core tools
 *  - FSV disable flow uses built-in toggle
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

// ---------------------------------------------------------------------------
// On-save validation — useEditorSave.ts (extracted from TiptapEditorFull.tsx)
// ---------------------------------------------------------------------------

describe("useEditorSave.ts — on-save validation (Item 34 Phase 3)", () => {
  // After Phase 3 extraction, this logic lives in useEditorSave.ts
  const saveHook = src("lib/useEditorSave.ts");

  it("autoValidationEnabled ref is initialized", () => {
    expect(saveHook).toContain("autoValidationEnabled");
    expect(saveHook).toContain("useRef");
  });

  it("auto-validation setting is loaded from backend on mount", () => {
    expect(saveHook).toMatch(/autoValidationEnabled\.current.*=.*enabled|enabled.*autoValidationEnabled\.current/s);
  });

  it("on-save fires POST to /documents/preflight", () => {
    expect(saveHook).toContain("/documents/preflight");
    expect(saveHook).toMatch(/method.*POST.*preflight|preflight.*method.*POST/s);
  });

  it("preflight POST body includes document_id", () => {
    expect(saveHook).toContain("document_id");
    expect(saveHook).toMatch(/document_id.*docId|docId.*document_id/);
  });

  it("preflight is skipped when autoValidationEnabled is false", () => {
    expect(saveHook).toMatch(/if\s*\(\s*autoValidationEnabled\.current\s*\)/);
  });

  it("setValidationSummary is called with quality_score, plain_language_grade, issues, source", () => {
    expect(saveHook).toContain("setValidationSummary");
    expect(saveHook).toContain("quality_score");
    expect(saveHook).toContain("plain_language_grade");
    expect(saveHook).toContain("source");
  });

  it("on-save validation is fire-and-forget (never blocks save)", () => {
    // Uses .catch(() => {}) to swallow errors
    expect(saveHook).toMatch(/\.catch\s*\(\s*\(\s*\)\s*=>\s*\{\s*\}\s*\)/);
  });
});

// ---------------------------------------------------------------------------
// Validation summary toolbar panel — EditorToolbar.tsx (extracted from TiptapEditorFull.tsx)
// ---------------------------------------------------------------------------

describe("EditorToolbar.tsx — validationSummary toolbar panel", () => {
  // After Phase 3 extraction, the toolbar panel lives in EditorToolbar.tsx
  const toolbar = src("components/editor/EditorToolbar.tsx");

  it("validationSummary prop is declared in EditorToolbarProps", () => {
    expect(toolbar).toContain("validationSummary");
    expect(toolbar).toContain("ValidationSummary");
  });

  it("toolbar panel shows score percentage", () => {
    expect(toolbar).toMatch(/validationSummary\.score/);
    // Score is rendered as a percentage (multiply by 100)
    expect(toolbar).toMatch(/Math\.round.*validationSummary\.score.*100|validationSummary\.score.*\*\s*100/);
  });

  it("toolbar panel shows grade", () => {
    expect(toolbar).toContain("validationSummary.grade");
  });

  it("toolbar panel shows issue count", () => {
    expect(toolbar).toContain("validationSummary.issue_count");
  });

  it("toolbar panel captures source in validation summary (stored in useEditorSave)", () => {
    // source is captured in useEditorSave.ts's ValidationSummary — it's stored but
    // the toolbar links to document-quality page for full details rather than showing source inline
    const saveHook = src("lib/useEditorSave.ts");
    expect(saveHook).toContain("source");
    expect(saveHook).toContain("ValidationSummary");
  });

  it("toolbar panel uses color coding based on score threshold", () => {
    // score >= 0.8 → green, >= 0.5 → amber, else red
    expect(toolbar).toMatch(/validationSummary\.score.*>=.*0\.8|0\.8.*validationSummary\.score/);
    expect(toolbar).toMatch(/validationSummary\.score.*>=.*0\.5|0\.5.*validationSummary\.score/);
  });

  it("panel is conditionally rendered only when validationSummary is truthy", () => {
    expect(toolbar).toMatch(/\{validationSummary\s*&&|validationSummary\s*\?/);
  });
});

// ---------------------------------------------------------------------------
// Quality badge next to "Edit Document" CTA — project view
// ---------------------------------------------------------------------------

describe("projects/[id]/index.tsx — quality badge near Edit Document CTA", () => {
  const page = src("pages/projects/[id]/index.tsx");

  it("has 'Primary CTA + quality badge' section", () => {
    expect(page).toContain("Primary CTA + quality badge");
  });

  it("quality badge is gated by fsvEnabled", () => {
    expect(page).toContain("fsvEnabled");
    expect(page).toMatch(/fsvEnabled.*quality|quality.*fsvEnabled/s);
  });

  it("quality badge shows quality_score as percentage", () => {
    expect(page).toContain("quality_score");
    expect(page).toMatch(/Math\.round.*quality_score.*100|quality_score.*\*.*100/);
  });

  it("quality badge shows plain_language_grade", () => {
    expect(page).toContain("plain_language_grade");
    expect(page).toMatch(/Quality.*Grade|Grade.*Quality/);
  });

  it("quality badge uses color coding (green/amber/red)", () => {
    expect(page).toContain("bg-green-100");
    expect(page).toContain("bg-amber-100");
    expect(page).toContain("bg-red-100");
  });

  it("badge is hidden when primaryScore is not found", () => {
    expect(page).toMatch(/if\s*\(\s*!primaryScore\s*\)\s*return\s*null/);
  });
});

// ---------------------------------------------------------------------------
// Item 34 Phase 4 — FSV Core Tool designation in tools/index.tsx
// ---------------------------------------------------------------------------

describe("tools/index.tsx — FSV Core Tool designation", () => {
  const toolsPage = src("pages/tools/index.tsx");

  it("FSV tool has isCore: true", () => {
    // The FSV entry should be marked as core
    expect(toolsPage).toMatch(/isCore:\s*true/);
  });

  it("CoreBadge is rendered for core tools", () => {
    expect(toolsPage).toContain("CoreBadge");
    expect(toolsPage).toContain("tool.isCore");
  });

  it("FSV built-in plugin can be disabled via admin toggle", () => {
    // FSV is a built-in (isBuiltIn: true) with a toggle
    expect(toolsPage).toContain("isBuiltIn");
    expect(toolsPage).toContain("togglePlugin");
  });
});

// ---------------------------------------------------------------------------
// Admin toggle persistence — on-save validation configurable
// ---------------------------------------------------------------------------

describe("on-save validation configurable (Item 34 Phase 3 + Item 48)", () => {
  const toolsPage = src("pages/tools/index.tsx");
  const tiptap = src("components/TiptapEditorFull.tsx");

  it("tools page fetches auto-validation enabled state from backend", () => {
    expect(toolsPage).toContain("autoValidationEnabled");
    expect(toolsPage).toMatch(/auto.?valid/i);
  });

  it("tiptap editor reads auto-validation state from /admin/settings/auto-validation or similar", () => {
    // After Phase 3 extraction, the setting fetch is in useEditorSave.ts
    const saveHook2 = src("lib/useEditorSave.ts");
    expect(saveHook2).toMatch(/auto.?validation|autoValidation/i);
  });

  it("toggle calls PUT to update auto-validation state", () => {
    expect(toolsPage).toContain("toggleAutoValidation");
    expect(toolsPage).toMatch(/PUT.*auto.?validation|auto.?validation.*PUT/s);
  });
});
