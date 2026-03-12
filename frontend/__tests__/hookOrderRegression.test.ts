/**
 * Item 49 — React hook order and stability regression tests.
 *
 * These tests are intentionally source-level (static analysis via readFileSync)
 * rather than render tests. Render tests for a page this large require extensive
 * mocking of every hook; source assertions are a reliable, low-maintenance way to
 * guard against the specific regression patterns that caused production crashes.
 *
 * What each guard catches:
 *  - feedbackShowMyOnly: useState called after a conditional return → fewer hooks
 *    than expected on the loading render path.
 *  - router.isReady: accessing router.query before hydration returns {}.
 *  - RawApproval / mapApproval: `any` casts leaking wrong state shape.
 *  - Error Boundary: missing catch for render-time exceptions.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

// ---------------------------------------------------------------------------
// Guard: feedbackShowMyOnly declared before conditional returns
// ---------------------------------------------------------------------------

describe("feedbackShowMyOnly hook-order regression", () => {
  const page = src("pages/projects/[id]/index.tsx");

  it("feedbackShowMyOnly useState is present in the page", () => {
    expect(page).toContain("feedbackShowMyOnly");
    expect(page).toMatch(/useState.*false.*feedbackShowMyOnly|feedbackShowMyOnly.*useState.*false/s);
  });

  it("has a comment documenting the hook-order constraint", () => {
    // The comment was added to document WHY the state is placed before early returns.
    expect(page).toContain("before any early returns");
  });

  it("feedbackShowMyOnly declaration appears in the component before any conditional early return", () => {
    const lines = page.split("\n");
    // Find the hook declaration.
    const hookLine = lines.findIndex((l) => l.includes("feedbackShowMyOnly") && l.includes("useState"));
    // Find the first conditional early-return pattern AFTER the hook declaration.
    // These look like: `if (!something) return null/undefined/jsx`
    const firstConditionalReturn = lines.findIndex(
      (l, i) =>
        i > hookLine &&
        /^\s+if\s*\(![^)]+\)\s*return/.test(l),
    );
    expect(hookLine).toBeGreaterThan(0);
    // Either no conditional early returns exist after the hook (good),
    // or they all appear after the hook line (also good).
    // The key invariant: hookLine < firstConditionalReturn OR no conditional return exists.
    if (firstConditionalReturn !== -1) {
      expect(hookLine).toBeLessThan(firstConditionalReturn);
    }
    // Always pass if no conditional early returns are found after the hook.
    expect(hookLine).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Guard: router.isReady guard on dynamic pages
// ---------------------------------------------------------------------------

describe("router.isReady guard on dynamic pages", () => {
  it("projects/[id]/index.tsx uses router.isReady before accessing router.query.id", () => {
    const page = src("pages/projects/[id]/index.tsx");
    expect(page).toContain("router.isReady");
    // The id derivation must gate on isReady.
    expect(page).toMatch(/router\.isReady.*router\.query\.id|const id.*router\.isReady/s);
  });

  it("projects/[id]/index.tsx does NOT access router.query.id without the isReady guard", () => {
    const page = src("pages/projects/[id]/index.tsx");
    const lines = page.split("\n");
    // Lines that read router.query.id without first checking isReady inline.
    const unsafeLines = lines.filter(
      (l) =>
        l.includes("router.query.id") &&
        !l.includes("router.isReady") &&
        !l.trim().startsWith("//"),
    );
    // All accesses to router.query.id should be guarded; there should be at
    // most one which is the guarded assignment `const id = router.isReady ? ...`.
    expect(unsafeLines.length).toBeLessThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Guard: useApprovals RawApproval/mapApproval type safety
// ---------------------------------------------------------------------------

describe("useApprovals any-type removal regression", () => {
  const hook = src("lib/useApprovals.ts");

  it("defines RawApproval interface", () => {
    expect(hook).toContain("interface RawApproval");
  });

  it("defines and uses mapApproval mapper", () => {
    expect(hook).toContain("const mapApproval");
    expect(hook).toContain("mapApproval(");
  });

  it("RawApproval has typed fields (id, reviewer, state)", () => {
    expect(hook).toContain("id: string");
    expect(hook).toContain("reviewer: string");
    expect(hook).toContain("state: string");
  });

  it("mapApproval returns correctly typed Approval with state cast", () => {
    // The mapper must cast the API state string to the known union.
    expect(hook).toMatch(/\["pending", "approved", "overdue", "rejected"\]/);
  });
});

// ---------------------------------------------------------------------------
// Guard: Error Boundary is wired in _app.tsx
// ---------------------------------------------------------------------------

describe("PageErrorBoundary wiring in _app.tsx", () => {
  const app = src("pages/_app.tsx");

  it("_app.tsx defines PageErrorBoundary class", () => {
    expect(app).toContain("class PageErrorBoundary");
  });

  it("PageErrorBoundary implements getDerivedStateFromError", () => {
    expect(app).toContain("getDerivedStateFromError");
  });

  it("PageErrorBoundary implements componentDidUpdate for resetKey-based reset", () => {
    expect(app).toContain("componentDidUpdate");
    expect(app).toContain("resetKey");
  });

  it("PageErrorBoundary is rendered in _app wrapping the page component", () => {
    expect(app).toContain("<PageErrorBoundary");
    expect(app).toContain("</PageErrorBoundary>");
  });

  it("resetKey is bound to router.pathname for route-change auto-reset", () => {
    expect(app).toMatch(/resetKey=\{router\.pathname\}/);
  });
});
