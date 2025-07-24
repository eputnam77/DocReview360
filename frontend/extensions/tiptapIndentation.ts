/**
 * TipTap extension adding indentation controls.
 */
import { Extension } from "@tiptap/core";
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
    addCommands() {
      return {
        indent: () => ({ commands }) => {
          return commands.updateAttributes("paragraph", (attrs: any) => ({
            ...attrs,
            "data-indent": ((attrs["data-indent"] as number) || 0) + 1,
          }));
        },
        outdent: () => ({ commands }) => {
          return commands.updateAttributes("paragraph", (attrs: any) => {
            const level = ((attrs["data-indent"] as number) || 0) - 1;
            return { ...attrs, "data-indent": Math.max(0, level) };
          });
        },
      };
    },
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
  });
}
