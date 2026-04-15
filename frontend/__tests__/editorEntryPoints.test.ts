import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const FRONTEND = resolve(__dirname, "..");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

describe("editor entry points", () => {
  const page = src("pages/editors/tiptap.tsx");

  it("keeps the TipTap page behind a client-only dynamic import", () => {
    expect(page).toContain("dynamic(");
    expect(page).toContain("ssr: false");
    expect(page).toContain("EditorSkeleton");
    expect(page).toContain('() => import("../../components/TiptapEditorFull")');
  });

  it("re-exports createTiptapApi from the server-safe helper module", () => {
    expect(page).toContain('export { createTiptapApi } from "../../lib/tiptapApi";');
    expect(page).not.toContain(
      'export { createTiptapApi } from "../../components/TiptapEditorFull";',
    );
  });
});
