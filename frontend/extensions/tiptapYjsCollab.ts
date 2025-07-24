/**
 * TipTap extension for Yjs real-time collaboration.
 */
import { Extension } from "@tiptap/core";
import type { Awareness } from "y-protocols/awareness";

/**
 * Barebones Yjs collaboration extension placeholder.
 */
/**
 * Lightweight Yjs collaboration wrapper. If `yjs` is not
 * available (e.g. in offline demos) the extension simply
 * does nothing but keeps the API surface stable.
 */
export function tiptapYjsCollab() {
  return Extension.create({
    name: "yjs-collab",
    async onCreate() {
      try {
        const yjs = await import("yjs");
        const { WebrtcProvider } = await import("y-webrtc");
        const doc = new yjs.Doc();
        const provider = new WebrtcProvider("tiptap-demo", doc);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (this.editor as any).storage.yjs = { doc, provider };
      } catch (err) {
        console.warn("Yjs collaboration not available", err);
      }
    },
    onDestroy() {
      // Clean up Yjs provider if it was created
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const storage = (this.editor as any).storage.yjs;
      storage?.provider?.destroy();
    },
  });
}
