/**
 * TipTap extension enforcing locked heading levels.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey, type EditorState, type Transaction } from "@tiptap/pm/state";
import type { Node as ProseMirrorNode, ResolvedPos } from "@tiptap/pm/model";

const HEADING_LOCK_PLUGIN_KEY = new PluginKey("heading-lock");
const HEADING_LOCK_REVERT_META = "heading-lock-revert";
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

function serializeLockedHeadings(doc: ProseMirrorNode): string {
  const lockedHeadings: unknown[] = [];
  doc.descendants((node) => {
    if (isLockedHeading(node)) {
      lockedHeadings.push(node.toJSON());
    }
    return true;
  });
  return JSON.stringify(lockedHeadings);
}

function lockedHeadingsUnchanged(transaction: Transaction, state: EditorState): boolean {
  if (!transaction.docChanged) {
    return true;
  }
  return serializeLockedHeadings(state.doc) === serializeLockedHeadings(transaction.doc);
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
    addGlobalAttributes() {
      return [
        {
          types: ["heading"],
          attributes: {
            lockedHeading: {
              default: null,
              parseHTML: () => null,
              renderHTML: (attributes) => {
                if (!LOCKED_LEVELS.has(Number(attributes.level))) {
                  return {};
                }
                return {
                  contenteditable: "false",
                  class: "heading-locked",
                };
              },
            },
          },
        },
      ];
    },
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
          filterTransaction(transaction, state) {
            return lockedHeadingsUnchanged(transaction, state);
          },
          appendTransaction(transactions, oldState, newState) {
            if (transactions.some((transaction) => transaction.getMeta(HEADING_LOCK_REVERT_META))) {
              return null;
            }
            if (!transactions.some((transaction) => transaction.docChanged)) {
              return null;
            }
            if (serializeLockedHeadings(oldState.doc) === serializeLockedHeadings(newState.doc)) {
              return null;
            }
            const revert = newState.tr;
            revert.setMeta(HEADING_LOCK_REVERT_META, true);
            revert.replaceWith(0, newState.doc.content.size, oldState.doc.content);
            return revert;
          },
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
