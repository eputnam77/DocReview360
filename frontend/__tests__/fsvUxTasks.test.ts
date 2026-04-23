import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

describe("document-quality FSV host page", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("reads NEXT_PUBLIC_FSV_FRONTEND_URL", () => {
    expect(page).toContain("NEXT_PUBLIC_FSV_FRONTEND_URL");
  });

  it("embeds the standalone FSV frontend in an iframe", () => {
    expect(page).toContain("<iframe");
    expect(page).toContain('title="Federal Style Validator"');
  });

  it("keeps the host page minimal so the FSV app owns the UI", () => {
    expect(page).not.toContain("/fsv/status");
    expect(page).not.toContain("Powered by Federal Style Validator");
    expect(page).not.toContain("Open in new tab");
    expect(page).not.toContain("Back to Tools configuration");
  });

  it("removes the legacy duplicated checker routes", () => {
    expect(page).not.toContain("/tools/checker");
    expect(page).not.toContain("/documents/validate");
    expect(page).not.toContain("/documents/public");
  });
});
