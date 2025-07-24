/**
 * TipTap extension enforcing locked heading levels.
 */
import { Extension } from "@tiptap/core";

/**
 * Extension skeleton for locking heading levels 1 and 2.
 * Actual ProseMirror logic omitted for brevity.
 */
/**
 * Prevent editing of level 1 and level 2 headings.
 * We intercept backspace/delete and selection changes
 * to keep those headings immutable. This is a basic
 * demonstration and not a fool-proof content lock.
 */
export function tiptapHeadingLock() {
  return Extension.create({
    name: "heading-lock",
    addKeyboardShortcuts() {
      const isLocked = (editor: any) => {
        const { $from } = editor.state.selection as any;
        const node = $from.node($from.depth);
        return (
          node.type.name === "heading" && [1, 2].includes(node.attrs.level)
        );
      };
      return {
        Backspace: ({ editor }) => isLocked(editor),
        Delete: ({ editor }) => isLocked(editor),
      };
    },
  });
}
