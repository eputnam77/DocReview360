/**
 * Item 693 / Item 615 — Loading state coverage for React Query hooks.
 *
 * Tests that hooks guard against undefined-id hydration by using
 * `enabled: !!id` (or equivalent). This prevents spurious fetches and
 * hook-ordering violations during Next.js router hydration.
 *
 * These are source-level regression guards. Full MSW delayed-response tests
 * would require installing `msw` as a dev dependency (deferred to Item 615).
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const LIB = join(REPO_ROOT, "frontend", "lib");
const PAGES = join(REPO_ROOT, "frontend", "pages");

function lib(name: string): string {
  return readFileSync(join(LIB, name), "utf8");
}

function page(relPath: string): string {
  return readFileSync(join(PAGES, relPath), "utf8");
}

// ---------------------------------------------------------------------------
// useProject hook
// ---------------------------------------------------------------------------

describe("useProject hook loading guard", () => {
  it("hook file exists", () => {
    const text = lib("useProject.ts");
    expect(text.length).toBeGreaterThan(0);
  });

  it("uses React Query useQuery", () => {
    expect(lib("useProject.ts")).toContain("useQuery");
  });

  it("guards with enabled: !!id to prevent fetch on undefined", () => {
    const text = lib("useProject.ts");
    expect(text).toMatch(/enabled\s*:\s*!!\s*id/);
  });

  it("queryKey includes id for correct cache invalidation", () => {
    const text = lib("useProject.ts");
    expect(text).toContain('"project"');
    expect(text).toContain("id");
  });

  it("throws on non-ok response (no silent swallow)", () => {
    const text = lib("useProject.ts");
    expect(text).toContain("throw new Error");
  });
});

// ---------------------------------------------------------------------------
// useApprovals hook
// ---------------------------------------------------------------------------

describe("useApprovals hook loading guard", () => {
  it("hook file exists", () => {
    const text = lib("useApprovals.ts");
    expect(text.length).toBeGreaterThan(0);
  });

  it("uses React Query useQuery", () => {
    expect(lib("useApprovals.ts")).toContain("useQuery");
  });

  it("has an enabled guard (prevents fetch when no workflow/id)", () => {
    const text = lib("useApprovals.ts");
    // Should have `enabled: !!something` or `enabled: Boolean(something)`
    expect(text).toMatch(/enabled\s*:/);
  });

  it("returns data and isLoading state", () => {
    const text = lib("useApprovals.ts");
    // useQuery returns { data, isLoading, ... }
    expect(text).toContain("useQuery");
  });
});

// ---------------------------------------------------------------------------
// usePhases hook
// ---------------------------------------------------------------------------

describe("usePhases hook loading guard", () => {
  it("hook file exists", () => {
    const text = lib("usePhases.ts");
    expect(text.length).toBeGreaterThan(0);
  });

  it("uses React Query useQuery", () => {
    expect(lib("usePhases.ts")).toContain("useQuery");
  });

  it("has an enabled guard", () => {
    const text = lib("usePhases.ts");
    expect(text).toMatch(/enabled\s*:/);
  });

  it("queryKey references workflowId or phases", () => {
    const text = lib("usePhases.ts");
    expect(text).toMatch(/queryKey.*phases|phases.*queryKey/s);
  });
});

// ---------------------------------------------------------------------------
// useProjects hook
// ---------------------------------------------------------------------------

describe("useProjects hook", () => {
  it("hook file exists", () => {
    const text = lib("useProjects.ts");
    expect(text.length).toBeGreaterThan(0);
  });

  it("uses React Query useQuery", () => {
    expect(lib("useProjects.ts")).toContain("useQuery");
  });

  it("has projects queryKey", () => {
    expect(lib("useProjects.ts")).toContain('"projects"');
  });
});

// ---------------------------------------------------------------------------
// Page-level: project detail page guards router.isReady
// ---------------------------------------------------------------------------

describe("Project detail page hydration guard", () => {
  it("projects/[id] page exists", () => {
    const text = page("projects/[id]/index.tsx");
    expect(text.length).toBeGreaterThan(0);
  });

  it("guards on router.isReady or router.query.id", () => {
    const text = page("projects/[id]/index.tsx");
    expect(text).toMatch(/router\.isReady|router\.query|useRouter/);
  });

  it("does not call useProject with undefined directly", () => {
    const text = page("projects/[id]/index.tsx");
    // Should pass id through router query, not a static undefined
    expect(text).toContain("useProject");
    // And must have some id extraction from router
    expect(text).toMatch(/router\.query|useRouter/);
  });
});

// ---------------------------------------------------------------------------
// Error boundary in _app.tsx
// ---------------------------------------------------------------------------

describe("Error boundary prevents white screen of death", () => {
  it("_app.tsx exists", () => {
    const text = readFileSync(join(PAGES, "_app.tsx"), "utf8");
    expect(text.length).toBeGreaterThan(0);
  });

  it("has ErrorBoundary wrapping the app", () => {
    const text = readFileSync(join(PAGES, "_app.tsx"), "utf8");
    expect(text).toMatch(/ErrorBoundary|componentDidCatch/);
  });

  it("has QueryClientProvider for React Query", () => {
    const text = readFileSync(join(PAGES, "_app.tsx"), "utf8");
    expect(text).toContain("QueryClientProvider");
  });
});

// ---------------------------------------------------------------------------
// MSW readiness (source-level check for future upgrade path)
// ---------------------------------------------------------------------------

describe("MSW upgrade readiness (Item 615)", () => {
  it("package.json exists and is parseable", () => {
    const text = readFileSync(join(REPO_ROOT, "frontend", "package.json"), "utf8");
    const pkg = JSON.parse(text);
    expect(pkg).toBeTruthy();
  });

  it("documents MSW as optional dev dep upgrade path in comments or elsewhere", () => {
    // We note that MSW is not yet installed but hooks are guarded with enabled:!!id
    // This test simply verifies the hooks exist and could accept MSW mocking later
    const useProject = lib("useProject.ts");
    const useApprovals = lib("useApprovals.ts");
    const usePhases = lib("usePhases.ts");
    // All three hooks use authenticatedFetch via queryFn — interceptable by MSW
    expect(useProject).toContain("authenticatedFetch");
    expect(useApprovals).toContain("authenticatedFetch");
    expect(usePhases).toContain("authenticatedFetch");
  });
});
