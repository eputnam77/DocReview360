/**
 * TipTap extension adding indentation controls.
 */
import { Extension, CommandProps } from "@tiptap/core";
import { Node as PMNode } from "prosemirror-model";

/**
 * Minimal indentation extension returning a blank command set.
 */
/**
 * Adds simple indent/outdent commands by storing the level
 * in a `data-indent` attribute on paragraphs and list items.
 */
export function tiptapIndentation() {
  return Extension.create({
    name: "indentation",
    addGlobalAttributes() {
      return [
        {
          types: ["paragraph", "listItem"],
          attributes: {
            "data-indent": {
              default: 0,
              parseHTML: (el: HTMLElement) => Number(el.getAttribute("data-indent")) || 0,
              renderHTML: (attrs: any) => {
                if (!attrs["data-indent"]) return {};
                return { "data-indent": attrs["data-indent"] };
              },
            },
          },
        },
      ];
    },
    addCommands() {
      return {
        indent:
          () =>
          ({ state, dispatch }: CommandProps): boolean => {
            const { from, to } = state.selection;
            const tr = state.tr;

            state.doc.nodesBetween(from, to, (node: PMNode, pos) => {
              if (node.type.name === "paragraph" || node.type.name === "listItem") {
                const level = (node.attrs["data-indent"] || 0) + 1;
                tr.setNodeMarkup(pos, undefined, {
                  ...node.attrs,
                  "data-indent": level,
                });
              }
            });

            if (tr.docChanged) {
              dispatch?.(tr);
              return true;
            }
            return false;
          },
        outdent:
          () =>
          ({ state, dispatch }: CommandProps): boolean => {
            const { from, to } = state.selection;
            const tr = state.tr;

            state.doc.nodesBetween(from, to, (node: PMNode, pos) => {
              if (node.type.name === "paragraph" || node.type.name === "listItem") {
                const level = (node.attrs["data-indent"] || 0) - 1;
                tr.setNodeMarkup(pos, undefined, {
                  ...node.attrs,
                  "data-indent": Math.max(level, 0),
                });
              }
            });

            if (tr.docChanged) {
              dispatch?.(tr);
              return true;
            }
            return false;
          },
      } as Record<string, any>;
    },
  });
}
