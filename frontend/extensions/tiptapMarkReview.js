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
            // Check if we're in a browser environment and the package might be available
            if (typeof window === 'undefined') {
                console.warn("MarkReview: Skipping in SSR environment");
                return;
            }
            try {
                // Use a more explicit approach with type assertion
                const mod = await eval('import("markreview")');
                if (mod && mod.attach) {
                    mod.attach(this.editor.view);
                    console.log("MarkReview: Successfully attached to editor");
                }
                else {
                    console.warn("MarkReview: Package not available or attach method not found");
                }
            }
            catch (err) {
                console.warn("MarkReview not available - package may need to be built or is not properly installed", err);
                // Continue without the extension rather than failing
            }
        },
    });
}
