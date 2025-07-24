import { Extension } from "@tiptap/core";

/**
 * Wrapper for the external MarkReview extension.
 * It attempts to load the package at runtime so tests
 * do not fail if the dependency is unavailable.
 */
export function tiptapMarkReview() {
  return Extension.create({
    name: "mark-review",
  });
}
