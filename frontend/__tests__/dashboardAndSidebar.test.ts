/**
 * Item 45 — Dashboard settings cog, sidebar role gating, and widget visibility.
 *
 * Source-level tests that guard the key behaviors:
 *  - Dashboard pages render a settings / customize button
 *  - Sidebar gates admin-only links by role
 *  - Widget visibility uses the /dashboard/visibility API endpoint
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
// Dashboard settings cog / customize button
// ---------------------------------------------------------------------------

describe("Dashboard — settings cog / customize button", () => {
  it("user.tsx has a customize/settings action button", () => {
    const page = src("pages/dashboard/user.tsx");
    // Either a Cog icon, 'customize', or 'settings' button.
    const hasCog = page.includes("Cog") || page.includes("customize") || page.includes("settings");
    expect(hasCog).toBe(true);
  });

  it("admin.tsx has a customize/settings action", () => {
    const page = src("pages/dashboard/admin.tsx");
    const hasCog =
      page.includes("Cog") ||
      page.includes("customize") ||
      page.includes("settings") ||
      page.includes("Settings");
    expect(hasCog).toBe(true);
  });

  it("manager.tsx has a customize/settings action", () => {
    const page = src("pages/dashboard/manager.tsx");
    const hasCog =
      page.includes("Cog") ||
      page.includes("customize") ||
      page.includes("settings") ||
      page.includes("Settings");
    expect(hasCog).toBe(true);
  });

  it("dashboard/settings.tsx page exists and handles widget preferences", () => {
    const page = src("pages/dashboard/settings.tsx");
    // Should reference visibility or widget preferences.
    const hasVisibility = page.includes("visibility") || page.includes("widget") || page.includes("preference");
    expect(hasVisibility).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Sidebar role-based navigation gating
// ---------------------------------------------------------------------------

describe("Sidebar — role-based navigation gating", () => {
  const sidebar = src("components/workflow/Sidebar.tsx");

  it("reads isAdmin from the user store", () => {
    expect(sidebar).toContain("isAdmin");
    expect(sidebar).toMatch(/useUserStore.*isAdmin|isAdmin.*useUserStore/s);
  });

  it("reads roles from the user store", () => {
    expect(sidebar).toContain("roles");
    expect(sidebar).toMatch(/useUserStore.*roles|roles.*useUserStore/s);
  });

  it("applies role-based dashboard navigation selection", () => {
    // dashboardNav should select admin/manager/user dashboard based on role.
    expect(sidebar).toMatch(/isAdmin|roles\.includes.*manager/);
    expect(sidebar).toContain("dashboardNav");
  });

  it("gates admin-only sidebar sections with isAdmin check", () => {
    expect(sidebar).toMatch(/isAdmin\s*&&/);
  });
});

// ---------------------------------------------------------------------------
// Widget visibility — API persistence
// ---------------------------------------------------------------------------

describe("Widget visibility — API-based persistence", () => {
  // The persistence logic lives in state/visibility.ts (used by settings.tsx).
  const visibilityState = src("state/visibility.ts");
  const settingsPage = src("pages/dashboard/settings.tsx");

  it("state/visibility.ts references /dashboard/visibility endpoint", () => {
    expect(visibilityState).toContain("/dashboard/visibility");
  });

  it("state/visibility.ts uses authenticatedFetch (not raw fetch)", () => {
    expect(visibilityState).toContain("authenticatedFetch");
    expect(visibilityState).not.toMatch(/(?<![a-zA-Z])fetch\s*\(\s*`\s*\$\{API\}\//);
  });

  it("state/visibility.ts uses PUT to persist widget preferences", () => {
    expect(visibilityState).toMatch(/PUT/);
  });

  it("settings.tsx imports and uses useDashboardVisibility", () => {
    expect(settingsPage).toContain("useDashboardVisibility");
  });

  it("settings.tsx renders widget checkboxes from visibility state", () => {
    expect(settingsPage).toContain("Widget Visibility");
    expect(settingsPage).toContain("checkbox");
  });

  it("settings.tsx has a Save button that calls save()", () => {
    expect(settingsPage).toMatch(/onClick.*save|save.*onClick/);
    expect(settingsPage).toContain("Save");
  });
});
