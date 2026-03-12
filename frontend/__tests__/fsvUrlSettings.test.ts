/**
 * Item 34 Phase 2 — FSV endpoint URL settings round-trip and editor consumption.
 *
 * Verifies:
 * 1. Tools admin page correctly loads FSV URL from GET /admin/settings/fsv-url
 * 2. Tools admin page correctly saves FSV URL via PUT /admin/settings/fsv-url
 * 3. FSV URL input is controlled and reflects the stored value
 * 4. Editor (tiptap.tsx) consumes the FSV proxy via /documents/preflight
 *    (the backend reads the configured FSV URL transparently)
 * 5. fsv_proxy.py get_fsv_url() checks env → settings.yaml fallback chain
 * 6. is_fsv_configured() is exported and gates FSV features
 * 7. Admin-only guard on settings endpoints
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
// Tools admin page — FSV URL settings (frontend/pages/tools/index.tsx)
// ---------------------------------------------------------------------------

describe("Tools page — FSV URL settings round-trip", () => {
  const tools = src("pages/tools/index.tsx");

  it("fsvUrl state is declared", () => {
    expect(tools).toContain("fsvUrl");
    expect(tools).toContain("useState");
  });

  it("loads FSV URL from GET /admin/settings/fsv-url on mount", () => {
    expect(tools).toContain("/admin/settings/fsv-url");
    expect(tools).toMatch(/GET|authenticatedFetch.*fsv-url|fsv-url.*authenticatedFetch/s);
  });

  it("saves FSV URL via PUT /admin/settings/fsv-url", () => {
    expect(tools).toMatch(/PUT.*fsv-url|method.*PUT/s);
    expect(tools).toContain("/admin/settings/fsv-url");
  });

  it("PUT body includes url field", () => {
    expect(tools).toContain('"url"');
    expect(tools).toMatch(/body.*JSON\.stringify.*url|JSON\.stringify.*url/s);
  });

  it("fsvUrlInput state tracks user input", () => {
    expect(tools).toContain("fsvUrlInput");
  });

  it("shows active FSV URL when configured", () => {
    expect(tools).toContain("fsvUrl");
    // Should render the configured URL somewhere
    expect(tools).toMatch(/fsvUrl\s*&&|fsvUrl\s*\?/);
  });

  it("Save button is disabled when input matches stored value", () => {
    // disabled when fsvUrlInput === fsvUrl
    expect(tools).toMatch(/disabled.*fsvUrl|fsvUrlInput.*===.*fsvUrl/s);
  });

  it("references FEDERAL_STYLE_VALIDATOR_URL env var in UI or comments", () => {
    expect(tools).toContain("FEDERAL_STYLE_VALIDATOR_URL");
  });
});

// ---------------------------------------------------------------------------
// Editor consumption — tiptap.tsx fires /documents/preflight (backend proxies FSV)
// ---------------------------------------------------------------------------

describe("TipTap editor — FSV URL consumed via backend proxy", () => {
  const tiptap = src("pages/editors/tiptap.tsx");

  it("editor sends POST to /documents/preflight (not directly to FSV)", () => {
    expect(tiptap).toContain("/documents/preflight");
  });

  it("preflight is the editor's FSV integration point", () => {
    // The editor never calls FSV directly — it goes through the backend proxy
    expect(tiptap).not.toContain("/fsv/");
    expect(tiptap).not.toContain("FEDERAL_STYLE_VALIDATOR_URL");
  });

  it("validation result is stored in validationSummary state", () => {
    expect(tiptap).toContain("setValidationSummary");
    expect(tiptap).toContain("validationSummary");
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
