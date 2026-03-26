/**
 * Item 48 — Tools index page status badges and admin controls.
 * Item 51 — Tools information architecture (FSV + Quality Checker collapsed).
 *
 * Source-level tests verifying:
 *  - StatusBadge renders Active / Disabled / Not-installed states
 *  - Cards use opacity-60 for disabled/not-installed tools
 *  - Admin-only Configure links are gated by isAdmin
 *  - Enable/Disable toggle buttons are gated by isAdmin + isBuiltIn
 *  - CommunityBadge is rendered for community tools
 *  - CoreBadge is rendered for core tools
 *  - Federal Style Validator is collapsed into Document Quality Checker
 *  - Document Quality Checker entry navigates to /tools/document-quality
 *  - Description mentions "Federal Style Validator"
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

const page = src("pages/tools/index.tsx");

// ---------------------------------------------------------------------------
// StatusBadge component — three states
// ---------------------------------------------------------------------------

describe("Tools index — StatusBadge component", () => {
  it("StatusBadge function is defined", () => {
    expect(page).toContain("function StatusBadge");
  });

  it("StatusBadge handles 'active' state with text 'Active'", () => {
    expect(page).toContain("Active");
  });

  it("StatusBadge handles 'disabled' state with text 'Disabled'", () => {
    expect(page).toContain("Disabled");
  });

  it("StatusBadge handles 'not-installed' state with text 'Not installed'", () => {
    expect(page).toContain("Not installed");
  });

  it("StatusBadge is rendered inside the tool card loop", () => {
    expect(page).toContain("<StatusBadge status={status}");
  });
});

// ---------------------------------------------------------------------------
// Card dimming — opacity-60 for disabled/not-installed
// ---------------------------------------------------------------------------

describe("Tools index — card dimming", () => {
  it("applies opacity-60 when tool is disabled or not-installed", () => {
    expect(page).toContain("opacity-60");
    expect(page).toMatch(/isDisabled.*isNotInstalled.*opacity-60|opacity-60.*isDisabled.*isNotInstalled/s);
  });

  it("removes shadow hover effect for disabled/not-installed cards", () => {
    expect(page).toMatch(/!isDisabled.*!isNotInstalled.*group-hover:shadow|group-hover:shadow.*!isDisabled.*!isNotInstalled/s);
  });
});

// ---------------------------------------------------------------------------
// Community badge
// ---------------------------------------------------------------------------

describe("Tools index — CommunityBadge", () => {
  it("CommunityBadge function is defined", () => {
    expect(page).toContain("function CommunityBadge");
  });

  it("CommunityBadge is conditionally rendered based on isCommunity flag", () => {
    expect(page).toContain("isCommunity && <CommunityBadge");
  });

  it("isCommunityTool helper is defined", () => {
    expect(page).toContain("function isCommunityTool");
  });
});

// ---------------------------------------------------------------------------
// CoreBadge
// ---------------------------------------------------------------------------

describe("Tools index — CoreBadge", () => {
  it("CoreBadge function is defined", () => {
    expect(page).toContain("function CoreBadge");
  });

  it("CoreBadge is rendered only when tool.isCore is truthy", () => {
    expect(page).toContain("tool.isCore && <CoreBadge");
  });
});

// ---------------------------------------------------------------------------
// Admin-only Configure links
// ---------------------------------------------------------------------------

describe("Tools index — admin Configure links", () => {
  it("Configure links are gated by isAdmin check", () => {
    expect(page).toMatch(/isAdmin.*configHref.*Configure|isAdmin.*&&.*Configure/s);
  });

  it("Configure links have configHref as href", () => {
    expect(page).toMatch(/tool\.configHref/);
  });

  it("isAdmin is read from the user store", () => {
    expect(page).toContain("isAdmin");
    expect(page).toMatch(/useUserStore.*isAdmin|isAdmin.*useUserStore/s);
  });
});

// ---------------------------------------------------------------------------
// Admin-only Enable/Disable toggle for built-in plugins
// ---------------------------------------------------------------------------

describe("Tools index — Enable/Disable toggle", () => {
  it("toggle button is gated by isAdmin and tool.isBuiltIn", () => {
    expect(page).toMatch(/isAdmin.*tool\.isBuiltIn|isAdmin.*&&.*isBuiltIn/s);
  });

  it("toggle button text alternates between Enable and Disable", () => {
    expect(page).toContain("Disable");
    expect(page).toContain("Enable");
  });

  it("togglePlugin function is defined", () => {
    expect(page).toContain("togglePlugin");
  });

  it("toggle calls /plugin-marketplace/toggle endpoint", () => {
    expect(page).toContain("/plugin-marketplace/toggle");
  });

  it("builtinStatus is loaded from /plugin-marketplace/builtin-status", () => {
    expect(page).toContain("/plugin-marketplace/builtin-status");
  });
});

// ---------------------------------------------------------------------------
// getStatus logic
// ---------------------------------------------------------------------------

describe("Tools index — getStatus logic", () => {
  it("getStatus function is defined", () => {
    expect(page).toContain("function getStatus");
  });

  it("returns 'disabled' when builtinStatus marks the tool as false", () => {
    expect(page).toContain("builtinStatus[tool.id] === false");
    expect(page).toMatch(/return\s+["']disabled["']/);
  });

  it("returns 'active' when plugins are installed", () => {
    expect(page).toMatch(/return\s+["']active["']/);
  });

  it("returns 'not-installed' for uninstalled community tools", () => {
    expect(page).toMatch(/return\s+["']not-installed["']/);
  });
});

// ---------------------------------------------------------------------------
// Item 51 — Tools IA: FSV collapsed into Document Quality Checker
// ---------------------------------------------------------------------------

describe("Tools index — Item 51 tools information architecture", () => {
  it("Document Quality Checker entry is present", () => {
    expect(page).toContain("Document Quality Checker");
  });

  it("Document Quality Checker navigates to /tools/document-quality", () => {
    expect(page).toContain('href: "/tools/document-quality"');
  });

  it("Document Quality Checker description mentions Federal Style Validator", () => {
    expect(page).toMatch(/Federal Style Validator/);
  });

  it("Document Quality Checker is marked as core (isCore: true)", () => {
    // The merged entry should be core
    expect(page).toMatch(/isCore:\s*true/);
  });

  it("Document Quality Checker is a built-in tool (isBuiltIn: true)", () => {
    expect(page).toMatch(/isBuiltIn:\s*true/);
  });

  it("Document Converter standalone entry is still present", () => {
    expect(page).toContain("Document Converter");
    expect(page).toContain('href: "/tools/converter"');
  });

  it("there is no separate standalone Federal Style Validator top-level entry", () => {
    // The FSV should NOT appear as its own separate card entry with id fedstylevalidator
    expect(page).not.toMatch(/id:\s*["']fedstylevalidator["']/);
  });
});
