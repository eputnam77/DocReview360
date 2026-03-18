/**
 * TipTap extension enforcing locked heading levels.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey, type EditorState } from "@tiptap/pm/state";
import type { Node as ProseMirrorNode, ResolvedPos } from "@tiptap/pm/model";

const HEADING_LOCK_PLUGIN_KEY = new PluginKey("heading-lock");
const LOCKED_LEVELS = new Set([1, 2]);
const BLOCKED_EDIT_KEYS = new Set(["Backspace", "Delete", "Enter", "Tab"]);
const BLOCKED_SHORTCUT_KEYS = new Set(["x", "v", "z", "y"]);

function isLockedHeading(node: ProseMirrorNode | null | undefined): boolean {
  return Boolean(
    node &&
      node.type.name === "heading" &&
      LOCKED_LEVELS.has(Number(node.attrs.level)),
  );
}

function isPositionInsideLockedHeading(position: ResolvedPos): boolean {
  for (let depth = position.depth; depth >= 0; depth -= 1) {
    if (isLockedHeading(position.node(depth))) {
      return true;
    }
  }
  return false;
}

function selectionTouchesLockedHeading(state: EditorState): boolean {
  const { $from, $to } = state.selection;
  return isPositionInsideLockedHeading($from) || isPositionInsideLockedHeading($to);
}

function shouldBlockKey(event: KeyboardEvent): boolean {
  if (BLOCKED_EDIT_KEYS.has(event.key)) {
    return true;
  }

  if (event.key.length === 1 && !(event.ctrlKey || event.metaKey || event.altKey)) {
    return true;
  }

  if (
    (event.ctrlKey || event.metaKey) &&
    BLOCKED_SHORTCUT_KEYS.has(event.key.toLowerCase())
  ) {
    return true;
  }

  return false;
}

function shouldBlockBeforeInput(event: InputEvent): boolean {
  return Boolean(event.inputType) && (
    event.inputType.startsWith("insert") ||
    event.inputType.startsWith("delete") ||
    event.inputType === "historyUndo" ||
    event.inputType === "historyRedo"
  );
}

export function tiptapHeadingLock() {
  return Extension.create({
    name: "heading-lock",
    addKeyboardShortcuts() {
      const isLocked = ({ editor }: { editor: { state: EditorState } }) =>
        selectionTouchesLockedHeading(editor.state);
      return {
        Backspace: (props) => isLocked(props),
        Delete: (props) => isLocked(props),
      };
    },
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: HEADING_LOCK_PLUGIN_KEY,
          props: {
            handleTextInput(view) {
              return selectionTouchesLockedHeading(view.state);
            },
            handlePaste(view) {
              return selectionTouchesLockedHeading(view.state);
            },
            handleDrop(view) {
              return selectionTouchesLockedHeading(view.state);
            },
            handleKeyDown(view, event) {
              if (!selectionTouchesLockedHeading(view.state) || !shouldBlockKey(event)) {
                return false;
              }
              event.preventDefault();
              return true;
            },
            handleDOMEvents: {
              beforeinput(view, event) {
                if (
                  !(event instanceof InputEvent) ||
                  !selectionTouchesLockedHeading(view.state) ||
                  !shouldBlockBeforeInput(event)
                ) {
                  return false;
                }
                event.preventDefault();
                return true;
              },
            },
          },
        }),
      ];
    },
  });
}
