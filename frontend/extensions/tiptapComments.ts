/**
 * DocReview360 TipTap Comments Extension
 *
 * A TipTap Mark extension that anchors inline comments to selected text.
 * Each comment mark stores a `commentId` (UUID) and an optional `metadata`
 * JSON blob (author, timestamp, text preview).
 *
 * Marked text is highlighted with a light yellow background so reviewers
 * can spot anchored comments at a glance.
 *
 * Registered in frontend/extensions/registry.ts as a lazy toggleable plugin.
 *
 * Contract compliance:
 *   - Uses Mark.create() only (NO prototype mutation).
 *   - Degrades gracefully: the mark is a no-op if the extension is not loaded.
 */

import { Mark, mergeAttributes } from "@tiptap/core";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    commentMark: {
      /**
       * Add an inline comment mark to the current selection.
       * @param commentId  A stable UUID for the comment.
       * @param metadata   Optional JSON-serializable metadata (author, text, ts).
       */
      addComment: (commentId: string, metadata?: Record<string, unknown>) => ReturnType;
      /**
       * Remove the comment mark with the given commentId from the entire document.
       */
      removeComment: (commentId: string) => ReturnType;
    };
  }
}

/** Attributes stored on every comment mark node. */
export interface CommentMarkAttrs {
  /** Stable UUID that links this mark to the comment in the feedback ledger. */
  commentId: string;
  /** JSON-encoded metadata: { author, text, timestamp }. */
  metadata: string | null;
}

/**
 * CommentMark — a TipTap Mark that wraps selected text with a comment anchor.
 *
 * HTML rendering:  <span data-comment-id="…" data-comment-meta="…">…</span>
 * CSS highlight:   background-color: #fef9c3  (Tailwind yellow-100 equivalent)
 */
export const CommentMark = Mark.create<Record<string, never>, Record<string, never>>({
  name: "commentMark",

  /** Keep the mark when content is copy-pasted or split across nodes. */
  inclusive: false,
  spanning: true,
  keepOnSplit: true,

  addAttributes() {
    return {
      commentId: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-comment-id"),
        renderHTML: (attrs) => {
          if (!attrs.commentId) return {};
          return { "data-comment-id": attrs.commentId };
        },
      },
      metadata: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-comment-meta") ?? null,
        renderHTML: (attrs) => {
          if (!attrs.metadata) return {};
          return { "data-comment-meta": attrs.metadata };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: "span[data-comment-id]",
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(HTMLAttributes, {
        class: "tiptap-comment-mark",
        style: "background-color:#fef9c3;border-bottom:2px solid #ca8a04;cursor:pointer;",
      }),
      0,
    ];
  },

  addCommands() {
    return {
      addComment:
        (commentId: string, metadata?: Record<string, unknown>) =>
        ({ commands }) => {
          const metaStr = metadata ? JSON.stringify(metadata) : null;
          return commands.setMark(this.name, { commentId, metadata: metaStr });
        },

      removeComment:
        (commentId: string) =>
        ({ tr, dispatch }) => {
          const { doc } = tr;
          let found = false;

          doc.descendants((node, pos) => {
            if (!node.isText) return;
            node.marks.forEach((mark) => {
              if (mark.type.name === "commentMark" && mark.attrs.commentId === commentId) {
                found = true;
                if (dispatch) {
                  tr.removeMark(pos, pos + node.nodeSize, mark.type);
                }
              }
            });
          });

          if (found && dispatch) dispatch(tr);
          return found;
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      // Mod-Alt-m — shortcut is already wired in the keyboard-shortcuts extension;
      // re-exposing here so the shortcut is also callable from a toolbar button.
      "Mod-Alt-m": () => {
        const commentId = crypto.randomUUID
          ? crypto.randomUUID()
          : `c-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        return (this.editor.chain() as any).focus().addComment(commentId).run();
      },
    };
  },
});

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

/**
 * Walk a TipTap JSON doc and collect all comment marks.
 * Returns an array of { commentId, metadata, from, to } objects suitable
 * for posting to the feedback ledger.
 */
export interface ExtractedComment {
  commentId: string;
  metadata: Record<string, unknown> | null;
  /** Character positions in the ProseMirror document (approximate when doc is JSON). */
  from: number;
  to: number;
  text: string;
}

function walkNode(
  node: Record<string, unknown>,
  results: ExtractedComment[],
  pos: { value: number },
): void {
  const type = node.type as string | undefined;
  const isText = type === "text";

  if (isText) {
    const marks = (node.marks as Array<Record<string, unknown>> | undefined) ?? [];
    const text = (node.text as string) ?? "";
    const from = pos.value;
    const to = pos.value + text.length;

    for (const mark of marks) {
      if (mark.type === "commentMark") {
        const attrs = (mark.attrs as Record<string, string | null>) ?? {};
        const commentId = attrs.commentId ?? "";
        let metadata: Record<string, unknown> | null = null;
        if (attrs.metadata) {
          try {
            metadata = JSON.parse(attrs.metadata) as Record<string, unknown>;
          } catch {
            /* ignore malformed metadata */
          }
        }
        if (commentId) {
          results.push({ commentId, metadata, from, to, text });
        }
      }
    }
    pos.value = to;
    return;
  }

  // Non-text nodes: advance pos by 1 (opening token) and recurse into content.
  pos.value += 1;
  const content = (node.content as Array<Record<string, unknown>> | undefined) ?? [];
  for (const child of content) {
    walkNode(child, results, pos);
  }
  // Closing token for non-inline nodes.
  if (type !== "text") pos.value += 1;
}

/**
 * Extract all comment marks from a TipTap JSON document object.
 *
 * @param doc  The raw TipTap JSON document (`editor.getJSON()`).
 * @returns    Array of extracted comment data.
 */
export function extractCommentsFromDoc(
  doc: Record<string, unknown>,
): ExtractedComment[] {
  const results: ExtractedComment[] = [];
  const pos = { value: 0 };
  walkNode(doc, results, pos);
  return results;
}
