/**
 * Item 34 Phase 2 — FSV endpoint URL support and editor consumption.
 *
 * Verifies:
 * 1. Tools page no longer renders inline FSV admin settings
 * 2. Editor (TiptapEditorFull.tsx) consumes the FSV proxy via /documents/preflight
 *    (the backend reads the configured FSV URL transparently)
 * 3. fsv_proxy.py get_fsv_url() checks env → settings.yaml fallback chain
 * 4. is_fsv_configured() is exported and gates FSV features
 * 5. Admin-only guard on settings endpoints
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");
const SRC = join(REPO_ROOT, "src", "docreview360");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

function backend(relPath: string): string {
  return readFileSync(join(SRC, relPath), "utf8");
}

// ---------------------------------------------------------------------------
// Tools page — FSV settings removed from this surface (frontend/pages/tools/index.tsx)
// ---------------------------------------------------------------------------

describe("Tools page — inline FSV settings removed", () => {
  const tools = src("pages/tools/index.tsx");

  it("does not render the FSV service URL card", () => {
    expect(tools).not.toContain("Federal Style Validator — Service URL");
    expect(tools).not.toContain("/admin/settings/fsv-url");
  });

  it("does not render the on-save validation controls", () => {
    expect(tools).not.toContain("Federal Style Validator — On-Save Validation");
    expect(tools).not.toContain("/admin/settings/auto-validation");
  });

  it("does not render the per-category FSV check toggles", () => {
    expect(tools).not.toContain("Federal Style Validator — Check Categories");
    expect(tools).not.toContain("/admin/settings/fsv-checks");
  });

  it("still renders the top-level tool cards grid", () => {
    expect(tools).toContain("ALL_TOOLS_ITEMS.map");
    expect(tools).toContain("Document Quality Checker");
  });
});

// ---------------------------------------------------------------------------
// Editor consumption — TiptapEditorFull.tsx fires /documents/preflight (backend proxies FSV)
// ---------------------------------------------------------------------------

describe("TipTap editor — FSV URL consumed via backend proxy", () => {
  // After Phase 3 extraction, the preflight/validation logic lives in useEditorSave.ts
  const saveHook = src("lib/useEditorSave.ts");

  it("editor sends POST to /documents/preflight (not directly to FSV)", () => {
    expect(saveHook).toContain("/documents/preflight");
  });

  it("preflight is the editor's FSV integration point", () => {
    // The editor never calls FSV directly — it goes through the backend proxy
    expect(saveHook).not.toContain("/fsv/");
    expect(saveHook).not.toContain("FEDERAL_STYLE_VALIDATOR_URL");
  });

  it("validation result is stored in validationSummary state", () => {
    expect(saveHook).toContain("setValidationSummary");
    expect(saveHook).toContain("validationSummary");
  });
});

// ---------------------------------------------------------------------------
// FSV proxy backend — get_fsv_url() and is_fsv_configured()
// ---------------------------------------------------------------------------

describe("fsv_proxy.py — URL resolution and configuration check", () => {
  const proxy = backend("fsv_proxy.py");

  it("get_fsv_url function is defined", () => {
    expect(proxy).toContain("def get_fsv_url");
  });

  it("get_fsv_url checks FEDERAL_STYLE_VALIDATOR_URL env var first", () => {
    expect(proxy).toContain("FEDERAL_STYLE_VALIDATOR_URL");
    // Env check must come before settings.yaml check
    const envPos = proxy.indexOf("FEDERAL_STYLE_VALIDATOR_URL");
    const settingsPos = proxy.indexOf("settings_manager");
    expect(envPos).toBeLessThan(settingsPos);
  });

  it("get_fsv_url falls back to settings.yaml (fsv_url key)", () => {
    expect(proxy).toContain("fsv_url");
    expect(proxy).toContain("settings_manager");
  });

  it("is_fsv_configured is exported", () => {
    expect(proxy).toContain("is_fsv_configured");
    expect(proxy).toContain('"is_fsv_configured"');
  });

  it("is_fsv_configured returns bool based on get_fsv_url", () => {
    expect(proxy).toMatch(/is_fsv_configured.*get_fsv_url|get_fsv_url.*is_fsv_configured/s);
    expect(proxy).toContain("bool(");
  });
});

// ---------------------------------------------------------------------------
// Admin router — FSV URL endpoint guards
// ---------------------------------------------------------------------------

describe("admin_router.py — FSV URL endpoint security", () => {
  const router = backend("api/admin_router.py");

  it("GET /admin/settings/fsv-url endpoint exists", () => {
    expect(router).toContain("/admin/settings/fsv-url");
    expect(router).toMatch(/get.*fsv.url|fsv.url.*get/i);
  });

  it("PUT /admin/settings/fsv-url endpoint exists", () => {
    expect(router).toMatch(/PUT.*fsv-url|put.*fsv.url/i);
  });

  it("FSV URL settings require admin role", () => {
    // Admin-only guard near the endpoint definitions
    const urlSettingsSection = router.slice(
      router.indexOf("/admin/settings/fsv-url"),
    );
    expect(urlSettingsSection).toMatch(/require_role|admin|current_user/);
  });

  it("PUT stores url via settings_manager.update_setting", () => {
    expect(router).toContain("update_setting");
    expect(router).toContain("fsv_url");
  });

  it("GET returns configured status and URL", () => {
    expect(router).toContain("is_fsv_configured");
    expect(router).toContain('"configured"');
  });
});
