/**
 * Tests for the TipTap Comments and Track-Changes extensions.
 *
 * These tests cover:
 *  - CommentMark: attribute schema, extractCommentsFromDoc utility
 *  - TrackChanges: attribute schema, extractChangesFromDoc utility
 *  - Registry entries for both new plugins
 *  - No-core-patch contract compliance for the new extensions
 */

import { describe, it, expect } from "vitest";
import {
  extractCommentsFromDoc,
  type ExtractedComment,
} from "../extensions/tiptapComments";
import {
  extractChangesFromDoc,
  type ExtractedChange,
} from "../extensions/tiptapTrackChanges";
import {
  PLUGIN_REGISTRY,
  checkTipTapCompatibility,
  getPlugin,
  toggleablePlugins,
} from "../extensions/registry";

// ---------------------------------------------------------------------------
// Helper: build minimal TipTap JSON document objects
// ---------------------------------------------------------------------------

function makeDoc(
  ...paragraphs: Array<Array<{ text: string; marks?: Array<Record<string, unknown>> }>>
): Record<string, unknown> {
  return {
    type: "doc",
    content: paragraphs.map((nodes) => ({
      type: "paragraph",
      content: nodes.map((n) => ({
        type: "text",
        text: n.text,
        ...(n.marks ? { marks: n.marks } : {}),
      })),
    })),
  };
}

// ---------------------------------------------------------------------------
// 1. extractCommentsFromDoc
// ---------------------------------------------------------------------------

describe("extractCommentsFromDoc", () => {
  it("returns empty array for a doc with no comment marks", () => {
    const doc = makeDoc([{ text: "Hello world" }]);
    const result = extractCommentsFromDoc(doc);
    expect(result).toHaveLength(0);
  });

  it("extracts a single comment mark", () => {
    const doc = makeDoc([
      {
        text: "annotated",
        marks: [
          {
            type: "commentMark",
            attrs: { commentId: "abc-123", metadata: null },
          },
        ],
      },
    ]);
    const result = extractCommentsFromDoc(doc);
    expect(result).toHaveLength(1);
    const c = result[0] as ExtractedComment;
    expect(c.commentId).toBe("abc-123");
    expect(c.text).toBe("annotated");
    expect(c.metadata).toBeNull();
  });

  it("extracts metadata JSON when present", () => {
    const meta = { author: "alice", text: "Review this phrase" };
    const doc = makeDoc([
      {
        text: "some phrase",
        marks: [
          {
            type: "commentMark",
            attrs: { commentId: "xyz-999", metadata: JSON.stringify(meta) },
          },
        ],
      },
    ]);
    const result = extractCommentsFromDoc(doc);
    expect(result).toHaveLength(1);
    expect(result[0].metadata).toEqual(meta);
    expect(result[0].commentId).toBe("xyz-999");
  });

  it("handles malformed metadata JSON gracefully", () => {
    const doc = makeDoc([
      {
        text: "broken",
        marks: [
          {
            type: "commentMark",
            attrs: { commentId: "bad-meta", metadata: "{not valid json" },
          },
        ],
      },
    ]);
    // Should not throw; metadata falls back to null.
    expect(() => extractCommentsFromDoc(doc)).not.toThrow();
    const result = extractCommentsFromDoc(doc);
    expect(result).toHaveLength(1);
    expect(result[0].metadata).toBeNull();
  });

  it("extracts multiple comment marks from the same paragraph", () => {
    const doc = makeDoc([
      { text: "plain " },
      {
        text: "first comment",
        marks: [{ type: "commentMark", attrs: { commentId: "c1", metadata: null } }],
      },
      { text: " middle " },
      {
        text: "second comment",
        marks: [{ type: "commentMark", attrs: { commentId: "c2", metadata: null } }],
      },
    ]);
    const result = extractCommentsFromDoc(doc);
    expect(result).toHaveLength(2);
    expect(result.map((r) => r.commentId)).toEqual(["c1", "c2"]);
  });

  it("extracts comment marks across multiple paragraphs", () => {
    const doc = makeDoc(
      [{ text: "para1", marks: [{ type: "commentMark", attrs: { commentId: "p1", metadata: null } }] }],
      [{ text: "para2", marks: [{ type: "commentMark", attrs: { commentId: "p2", metadata: null } }] }],
    );
    const result = extractCommentsFromDoc(doc);
    expect(result).toHaveLength(2);
    expect(result.map((r) => r.commentId).sort()).toEqual(["p1", "p2"]);
  });

  it("skips text nodes without comment marks", () => {
    const doc = makeDoc([
      { text: "no mark here" },
      { text: "also plain" },
      {
        text: "has mark",
        marks: [{ type: "commentMark", attrs: { commentId: "only-one", metadata: null } }],
      },
    ]);
    const result = extractCommentsFromDoc(doc);
    expect(result).toHaveLength(1);
    expect(result[0].commentId).toBe("only-one");
  });

  it("records numeric from/to positions", () => {
    const doc = makeDoc([
      {
        text: "hello",
        marks: [{ type: "commentMark", attrs: { commentId: "pos-test", metadata: null } }],
      },
    ]);
    const result = extractCommentsFromDoc(doc);
    expect(typeof result[0].from).toBe("number");
    expect(typeof result[0].to).toBe("number");
    expect(result[0].to).toBeGreaterThan(result[0].from);
  });

  it("ignores non-commentMark marks", () => {
    const doc = makeDoc([
      {
        text: "bold text",
        marks: [{ type: "bold" }],
      },
    ]);
    expect(extractCommentsFromDoc(doc)).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// 2. extractChangesFromDoc
// ---------------------------------------------------------------------------

describe("extractChangesFromDoc", () => {
  it("returns empty array for a plain doc", () => {
    const doc = makeDoc([{ text: "no changes here" }]);
    expect(extractChangesFromDoc(doc)).toHaveLength(0);
  });

  it("extracts a tracked insertion", () => {
    const doc = makeDoc([
      {
        text: "inserted text",
        marks: [
          {
            type: "trackInsertion",
            attrs: { changeId: "ins-1", reviewer: "alice", timestamp: "2026-01-01T00:00:00Z" },
          },
        ],
      },
    ]);
    const result = extractChangesFromDoc(doc);
    expect(result).toHaveLength(1);
    const ch = result[0] as ExtractedChange;
    expect(ch.changeType).toBe("insertion");
    expect(ch.changeId).toBe("ins-1");
    expect(ch.reviewer).toBe("alice");
    expect(ch.text).toBe("inserted text");
  });

  it("extracts a tracked deletion", () => {
    const doc = makeDoc([
      {
        text: "deleted text",
        marks: [
          {
            type: "trackDeletion",
            attrs: { changeId: "del-1", reviewer: "bob", timestamp: "2026-01-02T00:00:00Z" },
          },
        ],
      },
    ]);
    const result = extractChangesFromDoc(doc);
    expect(result).toHaveLength(1);
    expect(result[0].changeType).toBe("deletion");
    expect(result[0].reviewer).toBe("bob");
  });

  it("distinguishes multiple changes by changeId", () => {
    const doc = makeDoc([
      {
        text: "ins",
        marks: [{ type: "trackInsertion", attrs: { changeId: "i1", reviewer: "alice", timestamp: "" } }],
      },
      {
        text: "del",
        marks: [{ type: "trackDeletion", attrs: { changeId: "d1", reviewer: "bob", timestamp: "" } }],
      },
    ]);
    const result = extractChangesFromDoc(doc);
    expect(result).toHaveLength(2);
    const insertions = result.filter((r) => r.changeType === "insertion");
    const deletions = result.filter((r) => r.changeType === "deletion");
    expect(insertions).toHaveLength(1);
    expect(deletions).toHaveLength(1);
  });

  it("records from/to positions for tracked changes", () => {
    const doc = makeDoc([
      {
        text: "tracked",
        marks: [{ type: "trackInsertion", attrs: { changeId: "pos", reviewer: "r", timestamp: "" } }],
      },
    ]);
    const result = extractChangesFromDoc(doc);
    expect(result[0].to).toBeGreaterThan(result[0].from);
  });

  it("ignores non-track marks", () => {
    const doc = makeDoc([
      { text: "plain", marks: [{ type: "italic" }] },
    ]);
    expect(extractChangesFromDoc(doc)).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// 3. Registry entries
// ---------------------------------------------------------------------------

describe("registry — comment-mark and track-changes entries", () => {
  it("comment-mark is registered in PLUGIN_REGISTRY", () => {
    const p = getPlugin("comment-mark");
    expect(p).toBeDefined();
    expect(p?.lazy).toBe(true);
    expect(p?.alwaysOn).toBe(false);
    expect(p?.experimental).toBeFalsy();
    expect(p?.importPath).toBe("./tiptapComments");
    expect(p?.exportName).toBe("CommentMark");
  });

  it("track-changes is registered in PLUGIN_REGISTRY", () => {
    const p = getPlugin("track-changes");
    expect(p).toBeDefined();
    expect(p?.lazy).toBe(true);
    expect(p?.alwaysOn).toBe(false);
    expect(p?.experimental).toBeFalsy();
    expect(p?.importPath).toBe("./tiptapTrackChanges");
    expect(p?.exportName).toBe("TrackChanges");
  });

  it("both new plugins appear in toggleablePlugins()", () => {
    const toggleable = toggleablePlugins().map((p) => p.name);
    expect(toggleable).toContain("comment-mark");
    expect(toggleable).toContain("track-changes");
  });

  it("tiptapRange for both new plugins covers >=2.0.0 <3.0.0", () => {
    for (const name of ["comment-mark", "track-changes"]) {
      const p = getPlugin(name)!;
      expect(p.tiptapRange).toMatch(/>=2\./);
      expect(p.tiptapRange).toMatch(/<3\./);
    }
  });

  it("checkTipTapCompatibility still passes for 2.26.1 with new plugins", () => {
    const result = checkTipTapCompatibility("2.26.1");
    expect(result.compatible).toBe(true);
    expect(result.incompatible.map((p) => p.name)).not.toContain("comment-mark");
    expect(result.incompatible.map((p) => p.name)).not.toContain("track-changes");
  });

  it("names are still unique after adding new plugins", () => {
    const names = PLUGIN_REGISTRY.map((p) => p.name);
    expect(new Set(names).size).toBe(names.length);
  });
});

// ---------------------------------------------------------------------------
// 4. No-core-patch contract
// ---------------------------------------------------------------------------

describe("no-core-patch contract — new extensions", () => {
  it("importing CommentMark does not mutate Extension.prototype", async () => {
    const { Extension } = await import("@tiptap/core");
    const before = Object.getOwnPropertyNames(Extension.prototype).sort();
    await import("../extensions/tiptapComments");
    const after = Object.getOwnPropertyNames(Extension.prototype).sort();
    expect(after).toEqual(before);
  });

  it("importing TrackChanges does not mutate Extension.prototype", async () => {
    const { Extension } = await import("@tiptap/core");
    const before = Object.getOwnPropertyNames(Extension.prototype).sort();
    await import("../extensions/tiptapTrackChanges");
    const after = Object.getOwnPropertyNames(Extension.prototype).sort();
    expect(after).toEqual(before);
  });

  it("importing both extensions does not add properties to @tiptap/core module", async () => {
    const core = await import("@tiptap/core");
    const keysBefore = Object.keys(core).sort();
    await import("../extensions/tiptapComments");
    await import("../extensions/tiptapTrackChanges");
    const keysAfter = Object.keys(core).sort();
    expect(keysAfter).toEqual(keysBefore);
  });
});
