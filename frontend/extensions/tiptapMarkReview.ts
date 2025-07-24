import { Extension } from "@tiptap/core";

/**
 * Wrapper for the external MarkReview extension.
 * It attempts to load the package at runtime so tests
 * do not fail if the dependency is unavailable.
 */
export function tiptapMarkReview() {
  return Extension.create({
    name: "mark-review",
    async onCreate() {
      try {
        const mod = await import("markreview");
        if (mod.attach) {
          mod.attach(this.editor.view);
        }
      } catch (err) {
        console.warn("MarkReview not available", err);
      }
    },
  });
}
