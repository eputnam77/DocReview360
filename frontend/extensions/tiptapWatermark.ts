/**
 * TipTap extension for customizable watermarks.
 */
import { Extension } from "@tiptap/core";
import { Plugin } from "prosemirror-state";

/**
 * Extension adding a simple watermark to the editor DOM.
 */
/**
 * Adds a watermark overlay inside the editor element.
 * The text is stored in the `data-watermark` attribute
 * of the editor DOM node.
 */
export function tiptapWatermark(text: string = "Sample") {
  return Extension.create({
    name: "watermark",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          view: (editorView) => {
            const div = document.createElement("div");
            div.textContent = text;
            div.style.cssText =
              "position:absolute;top:50%;left:50%;pointer-events:none;opacity:0.2;transform:translate(-50%,-50%);";
            editorView.dom.parentElement?.appendChild(div);
            return {
              destroy() {
                div.remove();
              },
            };
          },
        }),
      ];
    },
  });
}
