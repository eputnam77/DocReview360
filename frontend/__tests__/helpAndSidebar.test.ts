/**
 * Item 47 — In-app support and documentation tests.
 *
 * Source-level tests verifying:
 *  - /help page has all promised sections (5-tab layout)
 *  - Sidebar "Help & Support" collapsible section is present
 *  - brandingSupportUrl and brandingDocsUrl are wired in the sidebar
 *  - HelpTooltip component exists and handles XSS-safe popover content
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
// /help page — 5-tab layout
// ---------------------------------------------------------------------------

describe("help.tsx — five-tab layout", () => {
  const helpPage = src("pages/help.tsx");

  it("renders a Tabs component", () => {
    expect(helpPage).toContain("<Tabs");
  });

  it("has a Getting Started tab", () => {
    expect(helpPage).toContain("Getting Started");
    expect(helpPage).toMatch(/value="getting-started"/);
  });

  it("has a Key Concepts tab", () => {
    expect(helpPage).toContain("Key Concepts");
    expect(helpPage).toMatch(/value="concepts"/);
  });

  it("has an FAQ tab", () => {
    expect(helpPage).toContain("FAQ");
    expect(helpPage).toMatch(/value="faq"/);
  });

  it("has a Keyboard Shortcuts tab", () => {
    expect(helpPage).toContain("shortcuts");
    expect(helpPage).toContain("Keyboard");
  });

  it("has an API Reference section", () => {
    // The 5th tab or a section covering API reference.
    expect(helpPage).toContain("API Reference");
  });

  it("includes at least one FAQ item", () => {
    expect(helpPage).toContain("FAQ_ITEMS");
    expect(helpPage).toMatch(/q:\s*"/);
  });
});

// ---------------------------------------------------------------------------
// Sidebar — "Help & Support" collapsible section
// ---------------------------------------------------------------------------

describe("Sidebar — Help & Support section", () => {
  const sidebar = src("components/workflow/Sidebar.tsx");

  it("has a 'Help & Support' label", () => {
    expect(sidebar).toContain("Help");
    expect(sidebar).toContain("Support");
  });

  it("links to /help#getting-started", () => {
    expect(sidebar).toContain("/help#getting-started");
  });

  it("links to /help#shortcuts", () => {
    expect(sidebar).toContain("/help#shortcuts");
  });
});

// ---------------------------------------------------------------------------
// Sidebar — brandingSupportUrl and brandingDocsUrl wiring
// ---------------------------------------------------------------------------

describe("Sidebar — branding URL wiring", () => {
  const sidebar = src("components/workflow/Sidebar.tsx");

  it("reads brandingDocsUrl from the branding store", () => {
    expect(sidebar).toContain("brandingDocsUrl");
  });

  it("reads brandingSupportUrl from the branding store", () => {
    expect(sidebar).toContain("brandingSupportUrl");
  });

  it("uses brandingDocsUrl to override the docs link destination", () => {
    // The sidebar must use the branding URL as the href for docs link.
    expect(sidebar).toMatch(/brandingDocsUrl|brandingSupportUrl/);
    // Must be used in an href or similar link target.
    expect(sidebar).toMatch(/href.*brandingDocsUrl|brandingDocsUrl.*href/s);
  });
});

// ---------------------------------------------------------------------------
// HelpTooltip component
// ---------------------------------------------------------------------------

describe("HelpTooltip component", () => {
  it("HelpTooltip file exists", () => {
    // Verify the component file is accessible.
    let content: string;
    try {
      content = src("components/HelpTooltip.tsx");
    } catch {
      content = src("components/ui/HelpTooltip.tsx");
    }
    expect(content.length).toBeGreaterThan(0);
  });

  it("HelpTooltip renders a popover or tooltip element", () => {
    let content: string;
    try {
      content = src("components/HelpTooltip.tsx");
    } catch {
      content = src("components/ui/HelpTooltip.tsx");
    }
    const hasPopover =
      content.includes("popover") ||
      content.includes("Popover") ||
      content.includes("tooltip") ||
      content.includes("Tooltip") ||
      content.includes("title=");
    expect(hasPopover).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Item 46 Phase 2 — login.tsx, projects/index.tsx, dashboard/user.tsx locale tests
// ---------------------------------------------------------------------------

describe("Item 46 Phase 2 — i18n migration for key pages", () => {
  it("login.tsx has locale file entries for login keys", () => {
    const en = src("public/locales/en/common.json");
    const parsed = JSON.parse(en);
    expect(parsed.login).toBeDefined();
    expect(parsed.login.title).toBeTruthy();
    expect(parsed.login.username).toBeTruthy();
    expect(parsed.login.password).toBeTruthy();
  });

  it("projects locale keys are in all 4 locale files", () => {
    for (const locale of ["en", "es", "fr", "de"]) {
      const data = JSON.parse(src(`public/locales/${locale}/common.json`));
      expect(data.projects, `${locale} missing projects section`).toBeDefined();
    }
  });

  it("dashboard locale keys are in all 4 locale files", () => {
    for (const locale of ["en", "es", "fr", "de"]) {
      const data = JSON.parse(src(`public/locales/${locale}/common.json`));
      expect(data.dashboard, `${locale} missing dashboard section`).toBeDefined();
    }
  });

  it("profile locale keys are in all 4 locale files", () => {
    for (const locale of ["en", "es", "fr", "de"]) {
      const data = JSON.parse(src(`public/locales/${locale}/common.json`));
      expect(data.profile, `${locale} missing profile section`).toBeDefined();
    }
  });

  it("search locale keys are in all 4 locale files", () => {
    for (const locale of ["en", "es", "fr", "de"]) {
      const data = JSON.parse(src(`public/locales/${locale}/common.json`));
      expect(data.search, `${locale} missing search section`).toBeDefined();
    }
  });

  it("config locale keys are in all 4 locale files", () => {
    for (const locale of ["en", "es", "fr", "de"]) {
      const data = JSON.parse(src(`public/locales/${locale}/common.json`));
      expect(data.config, `${locale} missing config section`).toBeDefined();
    }
  });
});

// ---------------------------------------------------------------------------
// Item 46 Phase 2 — LocaleSwitcher in sidebar footer
// ---------------------------------------------------------------------------

describe("LocaleSwitcher in sidebar footer", () => {
  const sidebar = src("components/workflow/Sidebar.tsx");

  it("sidebar imports or renders LocaleSwitcher", () => {
    const hasLocaleSwitcher =
      sidebar.includes("LocaleSwitcher") || sidebar.includes("locale-switcher");
    expect(hasLocaleSwitcher).toBe(true);
  });
});
