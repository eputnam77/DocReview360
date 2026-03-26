/**
 * DocReview360 TipTap Track-Changes Extension
 *
 * Adds reviewer-attributed insertion and deletion marks to TipTap documents.
 *
 * - Insertions: green highlight + reviewer name attribute.
 * - Deletions:  red strikethrough + reviewer name attribute.
 * - acceptChange(id): accepts a tracked change (keeps insertions, removes deletions).
 * - rejectChange(id): rejects a tracked change (removes insertions, restores deletions).
 *
 * Each change is identified by a stable `changeId` UUID so individual changes
 * can be accepted/rejected independently.
 *
 * Registered in frontend/extensions/registry.ts as a lazy toggleable plugin.
 *
 * Contract compliance:
 *   - Uses Extension.create() + Mark.create() only (NO prototype mutation).
 *   - Degrades gracefully: no-op if the extension is not loaded.
 */

import { Extension, Mark, mergeAttributes } from "@tiptap/core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ChangeType = "insertion" | "deletion";

export interface TrackChangeAttrs {
  /** Stable UUID for this change. */
  changeId: string;
  /** "insertion" or "deletion". */
  changeType: ChangeType;
  /** The reviewer who made this change. */
  reviewer: string;
  /** ISO timestamp. */
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Insertion mark
// ---------------------------------------------------------------------------

/**
 * Mark for tracked insertions.
 * Rendered as: green background with reviewer tooltip.
 */
export const InsertionMark = Mark.create({
  name: "trackInsertion",

  inclusive: false,
  spanning: true,
  keepOnSplit: false,

  addAttributes() {
    return {
      changeId: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-change-id"),
        renderHTML: (attrs) => (attrs.changeId ? { "data-change-id": attrs.changeId } : {}),
      },
      reviewer: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-reviewer") ?? "",
        renderHTML: (attrs) => (attrs.reviewer ? { "data-reviewer": attrs.reviewer } : {}),
      },
      timestamp: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-timestamp") ?? "",
        renderHTML: (attrs) => (attrs.timestamp ? { "data-timestamp": attrs.timestamp } : {}),
      },
    };
  },

  parseHTML() {
    return [{ tag: "ins[data-change-id]" }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "ins",
      mergeAttributes(HTMLAttributes, {
        class: "tiptap-track-insertion",
        style:
          "background-color:#dcfce7;text-decoration:none;border-bottom:2px solid #16a34a;" +
          "cursor:pointer;",
        title: HTMLAttributes["data-reviewer"]
          ? `Inserted by ${HTMLAttributes["data-reviewer"]}`
          : "Inserted",
      }),
      0,
    ];
  },
});

// ---------------------------------------------------------------------------
// Deletion mark
// ---------------------------------------------------------------------------

/**
 * Mark for tracked deletions.
 * Rendered as: red strikethrough with reviewer tooltip.
 */
export const DeletionMark = Mark.create({
  name: "trackDeletion",

  inclusive: false,
  spanning: true,
  keepOnSplit: false,

  addAttributes() {
    return {
      changeId: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-change-id"),
        renderHTML: (attrs) => (attrs.changeId ? { "data-change-id": attrs.changeId } : {}),
      },
      reviewer: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-reviewer") ?? "",
        renderHTML: (attrs) => (attrs.reviewer ? { "data-reviewer": attrs.reviewer } : {}),
      },
      timestamp: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-timestamp") ?? "",
        renderHTML: (attrs) => (attrs.timestamp ? { "data-timestamp": attrs.timestamp } : {}),
      },
    };
  },

  parseHTML() {
    return [{ tag: "del[data-change-id]" }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "del",
      mergeAttributes(HTMLAttributes, {
        class: "tiptap-track-deletion",
        style:
          "color:#dc2626;text-decoration:line-through;background-color:#fee2e2;" +
          "cursor:pointer;",
        title: HTMLAttributes["data-reviewer"]
          ? `Deleted by ${HTMLAttributes["data-reviewer"]}`
          : "Deleted",
      }),
      0,
    ];
  },
});

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    trackChanges: {
      /**
       * Mark the current selection as an insertion by `reviewer`.
       */
      markInsertion: (reviewer: string, changeId?: string) => ReturnType;
      /**
       * Mark the current selection as a deletion by `reviewer`.
       */
      markDeletion: (reviewer: string, changeId?: string) => ReturnType;
      /**
       * Accept a tracked change: keeps insertions, removes deletion marks
       * (the underlying text is retained).
       */
      acceptChange: (changeId: string) => ReturnType;
      /**
       * Reject a tracked change: removes insertion marks (and their text),
       * removes deletion marks (the deleted text is kept but mark is removed).
       */
      rejectChange: (changeId: string) => ReturnType;
    };
  }
}

// ---------------------------------------------------------------------------
// Main extension
// ---------------------------------------------------------------------------

/**
 * TrackChanges — a TipTap Extension that composes InsertionMark + DeletionMark
 * and wires up the accept/reject commands.
 */
export const TrackChanges = Extension.create({
  name: "trackChanges",

  addExtensions() {
    return [InsertionMark, DeletionMark];
  },

  addCommands() {
    return {
      markInsertion:
        (reviewer: string, changeId?: string) =>
        ({ commands }) => {
          const id =
            changeId ??
            (typeof crypto !== "undefined" && crypto.randomUUID
              ? crypto.randomUUID()
              : `ins-${Date.now()}-${Math.random().toString(36).slice(2)}`);
          const timestamp = new Date().toISOString();
          return commands.setMark("trackInsertion", { changeId: id, reviewer, timestamp });
        },

      markDeletion:
        (reviewer: string, changeId?: string) =>
        ({ commands }) => {
          const id =
            changeId ??
            (typeof crypto !== "undefined" && crypto.randomUUID
              ? crypto.randomUUID()
              : `del-${Date.now()}-${Math.random().toString(36).slice(2)}`);
          const timestamp = new Date().toISOString();
          return commands.setMark("trackDeletion", { changeId: id, reviewer, timestamp });
        },

      acceptChange:
        (changeId: string) =>
        ({ tr, dispatch }) => {
          const { doc } = tr;
          let changed = false;

          // Remove deletion marks with this changeId (the deleted text stays).
          // Remove insertion marks with this changeId (the inserted text stays).
          doc.descendants((node, pos) => {
            if (!node.isText) return;
            for (const mark of node.marks) {
              if (
                (mark.type.name === "trackInsertion" ||
                  mark.type.name === "trackDeletion") &&
                mark.attrs.changeId === changeId
              ) {
                changed = true;
                if (dispatch) {
                  tr.removeMark(pos, pos + node.nodeSize, mark.type);
                }
              }
            }
          });

          if (changed && dispatch) dispatch(tr);
          return changed;
        },

      rejectChange:
        (changeId: string) =>
        ({ tr, dispatch, state }) => {
          const { doc } = tr;
          // Collect ranges to delete for insertions (text goes away on reject).
          const insertionRanges: Array<{ from: number; to: number }> = [];
          // Collect deletion marks to remove (text is "restored" — we just
          // remove the mark).
          const deletionMarkRanges: Array<{
            from: number;
            to: number;
            markType: any;
          }> = [];

          doc.descendants((node, pos) => {
            if (!node.isText) return;
            for (const mark of node.marks) {
              if (mark.attrs.changeId !== changeId) continue;
              if (mark.type.name === "trackInsertion") {
                insertionRanges.push({ from: pos, to: pos + node.nodeSize });
              } else if (mark.type.name === "trackDeletion") {
                deletionMarkRanges.push({
                  from: pos,
                  to: pos + node.nodeSize,
                  markType: mark.type,
                });
              }
            }
          });

          if (insertionRanges.length === 0 && deletionMarkRanges.length === 0) {
            return false;
          }

          if (dispatch) {
            // Remove deletion marks first (no content change).
            for (const { from, to, markType } of deletionMarkRanges) {
              tr.removeMark(from, to, markType);
            }
            // Delete inserted ranges in reverse order to keep positions valid.
            const sorted = insertionRanges.sort((a, b) => b.from - a.from);
            for (const { from, to } of sorted) {
              tr.delete(from, to);
            }
            dispatch(tr);
          }

          // Suppress unused-variable warning for `state`.
          void state;
          return true;
        },
    };
  },
});

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

export interface ExtractedChange {
  changeId: string;
  changeType: ChangeType;
  reviewer: string;
  timestamp: string;
  text: string;
  from: number;
  to: number;
}

/**
 * Walk a TipTap JSON document and extract all tracked-change marks.
 */
export function extractChangesFromDoc(
  doc: Record<string, unknown>,
): ExtractedChange[] {
  const results: ExtractedChange[] = [];

  function walk(node: Record<string, unknown>, pos: { value: number }): void {
    const type = node.type as string | undefined;

    if (type === "text") {
      const text = (node.text as string) ?? "";
      const from = pos.value;
      const to = from + text.length;
      const marks = (node.marks as Array<Record<string, unknown>> | undefined) ?? [];

      for (const mark of marks) {
        const markType = mark.type as string | undefined;
        if (markType !== "trackInsertion" && markType !== "trackDeletion") continue;
        const attrs = (mark.attrs as Record<string, string>) ?? {};
        if (attrs.changeId) {
          results.push({
            changeId: attrs.changeId,
            changeType: markType === "trackInsertion" ? "insertion" : "deletion",
            reviewer: attrs.reviewer ?? "",
            timestamp: attrs.timestamp ?? "",
            text,
            from,
            to,
          });
        }
      }
      pos.value = to;
      return;
    }

    pos.value += 1;
    const content = (node.content as Array<Record<string, unknown>> | undefined) ?? [];
    for (const child of content) {
      walk(child, pos);
    }
    if (type !== "text") pos.value += 1;
  }

  walk(doc, { value: 0 });
  return results;
}
