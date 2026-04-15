import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const FRONTEND = resolve(__dirname, "..");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

describe("project dialog contracts", () => {
  it("VersionDrawer relies on shared dialog semantics instead of manual escape wiring", () => {
    const drawer = src("components/project/VersionDrawer.tsx");

    expect(drawer).toContain("<Dialog open={open} onOpenChange={(v) => !v && onClose()}>");
    expect(drawer).not.toContain('role="dialog"');
    expect(drawer).not.toContain("onKeyDown");
  });

  it("ProjectDetailsPage approval history dialog relies on Dialog onOpenChange", () => {
    const page = src("pages/projects/[id]/index.tsx");

    expect(page).toContain("<Dialog open={showHistory} onOpenChange={setShowHistory}>");
    expect(page).not.toContain(
      '<DialogContent className="max-w-md" onKeyDown={(e) => e.key === "Escape" && setShowHistory(false)}>',
    );
  });
});
