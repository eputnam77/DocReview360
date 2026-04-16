/**
 * Brittleness fixes F-06 through F-14 — source-level regression tests.
 *
 * These tests verify structural invariants introduced by the brittleness-fix
 * pass and guard against accidental reversion during future refactors.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const LIB = join(REPO_ROOT, "frontend", "lib");
const PAGES = join(REPO_ROOT, "frontend", "pages");

function lib(name: string): string {
  return readFileSync(join(LIB, name), "utf8");
}

function page(...parts: string[]): string {
  return readFileSync(join(PAGES, ...parts), "utf8");
}

// ---------------------------------------------------------------------------
// F-06: saveRevision fires state setters after unmount
// ---------------------------------------------------------------------------

describe("F-06 useEditorSave — unmount guard", () => {
  const src = lib("useEditorSave.ts");

  it("declares isMounted ref", () => {
    expect(src).toContain("isMounted");
    expect(src).toContain("useRef(true)");
  });

  it("sets isMounted.current = false on unmount", () => {
    expect(src).toContain("isMounted.current = false");
  });

  it("guards at least one state setter with isMounted.current", () => {
    expect(src).toContain("if (isMounted.current)");
  });

  it("clears saveTimer on unmount", () => {
    expect(src).toContain("clearTimeout(saveTimer.current)");
  });

  it("guards setSaveStatus('offline') with isMounted check", () => {
    // offline branch
    expect(src).toMatch(/isMounted\.current.*setSaveStatus.*offline|setSaveStatus.*offline.*isMounted/s);
  });

  it("guards setSaveStatus('saving') with isMounted check", () => {
    expect(src).toMatch(/isMounted\.current.*setSaveStatus.*saving|setSaveStatus.*saving.*isMounted/s);
  });

  it("guards setSaveStatus('saved') with isMounted check", () => {
    expect(src).toMatch(/isMounted\.current.*setSaveStatus.*saved|setSaveStatus.*saved.*isMounted/s);
  });

  it("guards setPdfUrl with isMounted check", () => {
    expect(src).toMatch(/isMounted\.current.*setPdfUrl|setPdfUrl.*isMounted/s);
  });

  it("guards setValidationSummary with isMounted check", () => {
    expect(src).toMatch(/isMounted\.current.*setValidationSummary|setValidationSummary.*isMounted/s);
  });

  it("guards error setSaveStatus with isMounted check", () => {
    // The catch block calls setSaveStatus(status) — must be guarded
    expect(src).toMatch(/isMounted\.current[\s\S]{0,40}setSaveStatus\(status\)|setSaveStatus\(status\)[\s\S]{0,10}isMounted/);
  });
});

// ---------------------------------------------------------------------------
// F-07: API response shapes assumed without null-checks
// ---------------------------------------------------------------------------

describe("F-07 useReviewerManagement — POST /approvals null guard", () => {
  const src = lib("useReviewerManagement.ts");

  it("guards created.id before setApprovals", () => {
    expect(src).toMatch(/!created\?\.id|created\?\.id/);
  });

  it("guards created.reviewer before setApprovals", () => {
    expect(src).toMatch(/!created\?\.reviewer|created\?\.reviewer/);
  });

  it("throws on missing id or reviewer", () => {
    expect(src).toContain('throw new Error("Unexpected response shape from POST /approvals');
  });

  it("guard appears before setApprovals call", () => {
    const guardIdx = src.indexOf("!created?.id");
    const setIdx = src.indexOf("setApprovals((prev) => [");
    expect(guardIdx).toBeGreaterThan(-1);
    expect(setIdx).toBeGreaterThan(-1);
    expect(guardIdx).toBeLessThan(setIdx);
  });
});

describe("F-07 projects/[id]/index.tsx — audit log null coalescing", () => {
  const src = page("projects", "[id]", "index.tsx");

  it("uses d?.details?.approvalId with null coalescing", () => {
    expect(src).toMatch(/d\?\.details\?\.approvalId/);
  });

  it("uses ?? null for the ref fallback", () => {
    expect(src).toContain("?? null");
  });
});

// ---------------------------------------------------------------------------
// F-09: Best-effort fetch swallows errors silently
// ---------------------------------------------------------------------------

describe("F-09 useProjectPageData — view-tracking catch logs warning", () => {
  const src = lib("useProjectPageData.ts");

  it("view-tracking catch uses console.warn, not empty handler", () => {
    // The catch for assignments/view should contain console.warn
    expect(src).toContain('console.warn("[view-tracking]');
  });

  it("does NOT have a silent empty catch for view-tracking", () => {
    // An empty catch looks like .catch(() => {}), but the view-tracking one must be replaced
    // We verify the warn is present; we don't prohibit all empty catches (there may be others)
    expect(src).not.toMatch(/\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\).*assignments\/view|assignments\/view.*\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)/s);
  });
});

// ---------------------------------------------------------------------------
// F-10: Template picker listener accumulation
// ---------------------------------------------------------------------------

describe("F-10 useEditorTemplates — ref-based mousedown debounce", () => {
  const src = lib("useEditorTemplates.ts");

  it("declares pickerListenerRef", () => {
    expect(src).toContain("pickerListenerRef");
  });

  it("removes listener before adding a new one", () => {
    // The new pattern explicitly removes the old listener before adding the new one
    const removeIdx = src.indexOf("document.removeEventListener");
    const addIdx = src.lastIndexOf("document.addEventListener");
    expect(removeIdx).toBeGreaterThan(-1);
    expect(addIdx).toBeGreaterThan(-1);
    // removeEventListener appears before addEventListener
    expect(removeIdx).toBeLessThan(addIdx);
  });

  it("sets pickerListenerRef.current to handler", () => {
    expect(src).toContain("pickerListenerRef.current = handler");
  });

  it("nulls pickerListenerRef.current in cleanup", () => {
    expect(src).toContain("pickerListenerRef.current = null");
  });
});

// ---------------------------------------------------------------------------
// F-11: Dead versions state removed, hook provides versions
// ---------------------------------------------------------------------------

describe("F-11 projects/[id]/index.tsx — dead versions state removed", () => {
  const src = page("projects", "[id]", "index.tsx");

  it("does NOT contain dead useState<VersionEntry[]>([])", () => {
    expect(src).not.toContain("useState<VersionEntry[]>([])");
  });

  it("versions appears in useProjectPageData destructuring", () => {
    // versions should be destructured from the useProjectPageData call
    // Match the const { ... } = useProjectPageData(...) block
    const destructureBlock = src.match(/const\s*\{[\s\S]*?\}\s*=\s*useProjectPageData\(/)?.[0] ?? "";
    expect(destructureBlock).toContain("versions");
  });
});

describe("F-11 useProjectPageData — exports versions", () => {
  const src = lib("useProjectPageData.ts");

  it("queries document versions", () => {
    expect(src).toContain("versions");
  });

  it("returns versions in the hook return value", () => {
    // versions should appear in the return object
    const returnBlock = src.match(/return \{[\s\S]*?\};/)?.[0] ?? "";
    expect(returnBlock).toContain("versions");
  });
});

// ---------------------------------------------------------------------------
// F-12: console.error replaced with console.warn
// ---------------------------------------------------------------------------

describe("F-12 usePhaseManagement — no console.error", () => {
  const src = lib("usePhaseManagement.ts");

  it("does NOT contain console.error(error)", () => {
    expect(src).not.toContain("console.error(error)");
  });

  it("contains console.warn with hook label", () => {
    expect(src).toContain('console.warn("[usePhaseManagement]"');
  });
});

describe("F-12 useReviewerManagement — no console.error", () => {
  const src = lib("useReviewerManagement.ts");

  it("does NOT contain console.error(error)", () => {
    expect(src).not.toContain("console.error(error)");
  });

  it("contains console.warn with hook label (handleUpdateReviewer)", () => {
    expect(src).toContain('console.warn("[useReviewerManagement]"');
  });

  it("all console.warn occurrences use hook label", () => {
    const matches = src.match(/console\.warn/g) ?? [];
    const labeled = src.match(/console\.warn\("\[useReviewerManagement\]"/g) ?? [];
    // Every console.warn should be labeled
    expect(labeled.length).toBe(matches.length);
  });
});

// ---------------------------------------------------------------------------
// F-14: id as string cast replaced with safeId
// ---------------------------------------------------------------------------

describe("F-14 projects/[id]/index.tsx — safeId replaces id as string cast", () => {
  const src = page("projects", "[id]", "index.tsx");

  it("does NOT contain useProject(id as string)", () => {
    expect(src).not.toContain("useProject(id as string)");
  });

  it("declares safeId with typeof guard", () => {
    expect(src).toMatch(/typeof id === "string"/);
  });

  it("uses safeId in useProject call", () => {
    expect(src).toContain("useProject(safeId)");
  });
});
