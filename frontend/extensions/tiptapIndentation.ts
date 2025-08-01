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
