/**
 * Accessibility — Task 4: Skip-to-main-content link
 *
 * Verifies that _app.tsx contains a skip link that:
 *  - targets #main-content
 *  - is visually hidden until focused (sr-only pattern)
 *  - becomes visible on focus (focus:not-sr-only)
 * And that the <main> element has id="main-content" and tabIndex={-1}
 * so keyboard users can skip past the sidebar.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, it, expect } from "vitest";

const FRONTEND = resolve(__dirname, "..");
const src = (rel: string) => readFileSync(join(FRONTEND, rel), "utf8");

describe("_app.tsx — skip-to-main-content link (Task 4)", () => {
  const app = src("pages/_app.tsx");

  it("contains a skip link element", () => {
    expect(app).toContain('href="#main-content"');
  });

  it("skip link text is 'Skip to main content'", () => {
    expect(app).toContain("Skip to main content");
  });

  it("skip link is hidden by default (sr-only)", () => {
    expect(app).toContain("sr-only");
  });

  it("skip link becomes visible on focus (focus:not-sr-only)", () => {
    expect(app).toContain("focus:not-sr-only");
  });

  it("skip link has a visible focus style", () => {
    expect(app).toMatch(/focus:bg-|focus:ring-/);
  });

  it("skip link is placed before Sidebar in the DOM", () => {
    const skipIdx = app.indexOf('href="#main-content"');
    const sidebarIdx = app.indexOf("<Sidebar");
    expect(skipIdx).toBeGreaterThan(-1);
    expect(skipIdx).toBeLessThan(sidebarIdx);
  });

  it("<main> element has id='main-content'", () => {
    expect(app).toContain('id="main-content"');
  });

  it("<main> element has tabIndex={-1} to receive programmatic focus", () => {
    expect(app).toContain("tabIndex={-1}");
  });
});
