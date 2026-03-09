/**
 * TipTap extension for Yjs real-time collaboration (WebRTC transport).
 *
 * STATUS: EXPERIMENTAL — NOT integrated in the v0.1 release editor.
 *
 * The production editor (`frontend/pages/editors/tiptap.tsx`) uses the
 * official `@tiptap/extension-collaboration` extension together with a
 * `HocuspocusProvider` (server-backed WebSocket transport) instead of
 * the WebRTC transport implemented here.
 *
 * This extension is intentionally kept separate so it can be wired in as
 * an alternative transport in a future release.  It is NOT listed in the
 * `extensions` array passed to `useEditor()` in the production editor.
 *
 * Tracking issue: integrate `tiptapYjsCollab` (WebRTC) as an optional
 * transport alongside Hocuspocus.  Requires:
 *   - y-webrtc signalling server configuration
 *   - awareness / cursor UI wiring
 *   - feature flag to choose between HocuspocusProvider and WebRtcProvider
 *
 * The Python backend test skip guard is in `tests/test_collab_service.py`
 * (searches for the `y_py` package).  Real-time collaboration is
 * out-of-scope for v0.1 but the infrastructure is in place.
 */
import { Extension } from "@tiptap/core";
import type { Awareness } from "y-protocols/awareness";

/**
 * Lightweight Yjs collaboration wrapper using WebRTC transport. If `yjs` or
 * `y-webrtc` are not available (e.g. in offline mode) the extension simply
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
        const provider = new WebrtcProvider("tiptap-room", doc);

        (this.editor as any).storage.yjs = { doc, provider };
      } catch (err) {
        console.warn("Yjs collaboration not available", err);
      }
    },
    onDestroy() {
      // Clean up Yjs provider if it was created

      const storage = (this.editor as any).storage.yjs;
      storage?.provider?.destroy();
    },
  });
}
