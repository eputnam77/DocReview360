/**
 * Inline Comments and Track-Changes Extensions — Item 44, sub-items 3, 4, 5
 *
 * Source-level tests verifying:
 *   Item 44.3 — TipTap comments extension stores inline comments as anchored marks
 *   Item 44.4 — TipTap track-changes extension with reviewer attribution
 *   Item 44.5 — Submit Review extracts inline marks into the backend feedback ledger
 *
 * Follows the same source-level convention as fsvUxTasks.test.ts.
 * No rendering; assertions read TypeScript source and check key patterns exist.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");
const EXTENSIONS = join(FRONTEND, "extensions");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

function ext(relPath: string): string {
  return readFileSync(join(EXTENSIONS, relPath), "utf8");
}

// ---------------------------------------------------------------------------
// Item 44.3 — CommentMark extension (tiptapComments.ts)
// ---------------------------------------------------------------------------

describe("Item 44.3: CommentMark — inline comment anchoring (tiptapComments.ts)", () => {
  const code = ext("tiptapComments.ts");

  it("exports CommentMark", () => {
    expect(code).toContain("export const CommentMark");
  });

  it("extension name is 'commentMark'", () => {
    expect(code).toContain('name: "commentMark"');
  });

  it("uses Mark.create() — no prototype patching", () => {
    expect(code).toContain("Mark.create");
    expect(code).not.toContain(".prototype.");
  });

  it("stores commentId attribute (links to feedback ledger)", () => {
    expect(code).toContain("commentId");
    expect(code).toContain('"data-comment-id"');
  });

  it("stores metadata attribute (author, text, timestamp)", () => {
    expect(code).toContain("metadata");
    expect(code).toContain('"data-comment-meta"');
  });

  it("addComment command is defined", () => {
    expect(code).toContain("addComment:");
    expect(code).toMatch(/addComment.*commentId.*metadata/s);
  });

  it("removeComment command is defined", () => {
    expect(code).toContain("removeComment:");
    expect(code).toMatch(/removeComment.*commentId/s);
  });

  it("removeComment uses removeMark to clean up the anchor", () => {
    expect(code).toContain("removeMark");
  });

  it("renders <span> with data-comment-id (parseHTML target)", () => {
    expect(code).toContain("span[data-comment-id]");
  });

  it("highlighted with yellow background (#fef9c3)", () => {
    expect(code).toContain("#fef9c3");
  });

  it("has Mod-Alt-m keyboard shortcut", () => {
    expect(code).toContain('"Mod-Alt-m"');
  });

  it("keepOnSplit: true — mark survives Enter key in editor", () => {
    expect(code).toContain("keepOnSplit: true");
  });

  it("exports extractCommentsFromDoc utility", () => {
    expect(code).toContain("export function extractCommentsFromDoc");
  });

  it("extractCommentsFromDoc walks doc descendants for commentMark type", () => {
    expect(code).toContain('"commentMark"');
    expect(code).toContain("walkNode");
  });

  it("ExtractedComment interface has commentId, from, to, text fields", () => {
    expect(code).toContain("export interface ExtractedComment");
    expect(code).toContain("commentId:");
    expect(code).toContain("from:");
    expect(code).toContain("to:");
    expect(code).toContain("text:");
  });
});

// ---------------------------------------------------------------------------
// Item 44.4 — TrackChanges extension (tiptapTrackChanges.ts)
// ---------------------------------------------------------------------------

describe("Item 44.4a: InsertionMark — tracked insertion rendering", () => {
  const code = ext("tiptapTrackChanges.ts");

  it("exports InsertionMark", () => {
    expect(code).toContain("export const InsertionMark");
  });

  it("InsertionMark name is 'trackInsertion'", () => {
    expect(code).toContain('name: "trackInsertion"');
  });

  it("InsertionMark renders <ins> element", () => {
    expect(code).toContain('"ins"');
    expect(code).toContain("ins[data-change-id]");
  });

  it("InsertionMark uses green highlight style", () => {
    expect(code).toContain("#dcfce7");
    expect(code).toContain("#16a34a");
  });

  it("InsertionMark stores changeId attribute", () => {
    expect(code).toMatch(/changeId[\s\S]*?data-change-id/);
  });

  it("InsertionMark stores reviewer attribute", () => {
    expect(code).toContain("reviewer");
    expect(code).toContain('"data-reviewer"');
  });

  it("InsertionMark stores timestamp attribute", () => {
    expect(code).toContain("timestamp");
    expect(code).toContain('"data-timestamp"');
  });
});

describe("Item 44.4b: DeletionMark — tracked deletion rendering", () => {
  const code = ext("tiptapTrackChanges.ts");

  it("exports DeletionMark", () => {
    expect(code).toContain("export const DeletionMark");
  });

  it("DeletionMark name is 'trackDeletion'", () => {
    expect(code).toContain('name: "trackDeletion"');
  });

  it("DeletionMark renders <del> element", () => {
    expect(code).toContain('"del"');
    expect(code).toContain("del[data-change-id]");
  });

  it("DeletionMark uses red strikethrough style", () => {
    expect(code).toContain("#dc2626");
    expect(code).toContain("line-through");
    expect(code).toContain("#fee2e2");
  });
});

describe("Item 44.4c: TrackChanges — composed extension with accept/reject", () => {
  const code = ext("tiptapTrackChanges.ts");

  it("exports TrackChanges", () => {
    expect(code).toContain("export const TrackChanges");
  });

  it("TrackChanges name is 'trackChanges'", () => {
    expect(code).toContain('name: "trackChanges"');
  });

  it("uses Extension.create() — no prototype patching", () => {
    expect(code).toContain("Extension.create");
    expect(code).not.toContain(".prototype.");
  });

  it("addExtensions composes InsertionMark and DeletionMark", () => {
    expect(code).toContain("addExtensions");
    expect(code).toContain("InsertionMark");
    expect(code).toContain("DeletionMark");
  });

  it("markInsertion command is defined", () => {
    expect(code).toContain("markInsertion:");
  });

  it("markDeletion command is defined", () => {
    expect(code).toContain("markDeletion:");
  });

  it("acceptChange command is defined", () => {
    expect(code).toContain("acceptChange:");
  });

  it("rejectChange command is defined", () => {
    expect(code).toContain("rejectChange:");
  });

  it("markInsertion accepts reviewer and optional changeId params", () => {
    expect(code).toMatch(/markInsertion.*reviewer.*changeId|markInsertion.*changeId.*reviewer/s);
  });
});

// ---------------------------------------------------------------------------
// Registry: both extensions are registered
// ---------------------------------------------------------------------------

describe("Registry entries for comment-mark and track-changes", () => {
  const registry = src("extensions/registry.ts");

  it("comment-mark plugin is registered", () => {
    expect(registry).toContain('name: "comment-mark"');
  });

  it("comment-mark importPath points to tiptapComments", () => {
    expect(registry).toContain('"./tiptapComments"');
  });

  it("comment-mark exportName is CommentMark", () => {
    expect(registry).toMatch(/name.*comment-mark[\s\S]*?exportName.*CommentMark/s);
  });

  it("track-changes plugin is registered", () => {
    expect(registry).toContain('name: "track-changes"');
  });

  it("track-changes importPath points to tiptapTrackChanges", () => {
    expect(registry).toContain('"./tiptapTrackChanges"');
  });

  it("track-changes exportName is TrackChanges", () => {
    expect(registry).toMatch(/name.*track-changes[\s\S]*?exportName.*TrackChanges/s);
  });

  it("both plugins are lazy and toggleable (not alwaysOn)", () => {
    // comment-mark block — description is multi-line, use 600 chars
    const cmBlock = registry.slice(
      registry.indexOf('"comment-mark"'),
      registry.indexOf('"comment-mark"') + 600,
    );
    expect(cmBlock).toContain("lazy: true");
    expect(cmBlock).toContain("alwaysOn: false");

    // track-changes block
    const tcBlock = registry.slice(
      registry.indexOf('"track-changes"'),
      registry.indexOf('"track-changes"') + 600,
    );
    expect(tcBlock).toContain("lazy: true");
    expect(tcBlock).toContain("alwaysOn: false");
  });
});

// ---------------------------------------------------------------------------
// Item 44.5 — TiptapEditorFull.tsx: inline mark extraction and Submit Review integration
// ---------------------------------------------------------------------------

describe("Item 44.5: TiptapEditorFull.tsx — inline mark extraction on Submit Review", () => {
  const tiptap = src("components/TiptapEditorFull.tsx");

  it("imports CommentMark from tiptapComments", () => {
    expect(tiptap).toContain("tiptapComments");
    expect(tiptap).toContain("CommentMark");
  });

  it("imports TrackChanges from tiptapTrackChanges", () => {
    expect(tiptap).toContain("tiptapTrackChanges");
    expect(tiptap).toContain("TrackChanges");
  });

  it("commentMarkEnabled state is declared (default true)", () => {
    expect(tiptap).toContain("commentMarkEnabled");
    expect(tiptap).toMatch(/commentMarkEnabled.*useState.*true|useState.*true.*commentMarkEnabled/s);
  });

  it("trackChangesEnabled state is declared (default true)", () => {
    expect(tiptap).toContain("trackChangesEnabled");
    expect(tiptap).toMatch(/trackChangesEnabled.*useState.*true|useState.*true.*trackChangesEnabled/s);
  });

  it("CommentMark is pushed to editor extensions when commentMarkEnabled", () => {
    expect(tiptap).toMatch(/commentMarkEnabled[\s\S]*?CommentMark|CommentMark[\s\S]*?commentMarkEnabled/);
  });

  it("TrackChanges is pushed to editor extensions when trackChangesEnabled", () => {
    expect(tiptap).toMatch(/trackChangesEnabled[\s\S]*?TrackChanges|TrackChanges[\s\S]*?trackChangesEnabled/);
  });

  it("extractAndPostInlineMarks function is defined", () => {
    expect(tiptap).toContain("extractAndPostInlineMarks");
    expect(tiptap).toContain("useCallback");
  });

  it("extraction walks doc.descendants for commentMark type", () => {
    expect(tiptap).toContain("doc.descendants");
    expect(tiptap).toContain('"commentMark"');
  });

  it("extraction handles trackInsertion marks", () => {
    expect(tiptap).toContain('"trackInsertion"');
  });

  it("extraction handles trackDeletion marks", () => {
    expect(tiptap).toContain('"trackDeletion"');
  });

  it("inline items are POSTed to /projects/{projectId}/feedback", () => {
    expect(tiptap).toMatch(/projects\/\$\{projectId\}\/feedback/);
    expect(tiptap).toMatch(/method.*POST|POST.*method/);
  });

  it("feedback POST body includes source: 'inline'", () => {
    expect(tiptap).toContain('source: "inline"');
  });

  it("feedback POST body includes range_anchor with position string", () => {
    expect(tiptap).toContain("range_anchor");
    expect(tiptap).toMatch(/range_anchor.*range|range.*range_anchor/s);
  });

  it("extraction uses Promise.allSettled (non-fatal on partial failure)", () => {
    expect(tiptap).toContain("Promise.allSettled");
  });

  it("commentMark metadata is parsed from JSON before posting text", () => {
    expect(tiptap).toMatch(/JSON\.parse.*metadata|metadata.*JSON\.parse/);
    expect(tiptap).toContain("meta.text");
  });
});
