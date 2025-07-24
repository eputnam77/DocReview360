/**
 * TipTap extension for draggable sections using Heading 2 nodes.
 */
import { Extension, mergeAttributes } from "@tiptap/core";
import { Node } from "@tiptap/core";

/**
 * Basic extension representing draggable sections using Heading 2.
 */
/**
 * Section node consisting of a draggable block with a
 * level 2 heading at the top. This is a very light‑weight
 * implementation to demonstrate draggable sections.
 */
export function tiptapSectionNode() {
  return Node.create({
    name: "section-node",
    group: "block",
    draggable: true,
    content: "heading block*",
    parseHTML() {
      return [{ tag: "section" }];
    },
    renderHTML({ HTMLAttributes }) {
      return ["section", mergeAttributes(HTMLAttributes), 0];
    },
  });
}
