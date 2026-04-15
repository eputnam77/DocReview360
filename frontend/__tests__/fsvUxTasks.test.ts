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

  it("uses Federal Style Validator branding", () => {
    expect(page).toContain("Federal Style Validator");
    expect(page).toContain("Powered by Federal Style Validator");
  });

  it("checks backend status through /fsv/status", () => {
    expect(page).toContain("/fsv/status");
  });

  it("reads NEXT_PUBLIC_FSV_FRONTEND_URL", () => {
    expect(page).toContain("NEXT_PUBLIC_FSV_FRONTEND_URL");
  });

  it("embeds the standalone FSV frontend in an iframe", () => {
    expect(page).toContain("<iframe");
  });

  it("removes the legacy duplicated checker routes", () => {
    expect(page).not.toContain("/tools/checker");
    expect(page).not.toContain("/documents/validate");
    expect(page).not.toContain("/documents/public");
  });
});
