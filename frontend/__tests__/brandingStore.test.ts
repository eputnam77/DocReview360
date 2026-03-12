/**
 * Tests for state/branding.ts — end-to-end store behavior.
 *
 * Verifies:
 * - `initialize()` calls authenticatedFetch('/branding') (no ${API} prefix)
 * - Store is populated from API response data
 * - Graceful fallback to defaults when the API call fails
 * - `initialized` flag is set after first call
 * - Subsequent calls with force=false are no-ops
 * - Source file contains no forbidden `${API}` fetch pattern
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "fs";
import { join, resolve } from "path";

// ── Mock authenticatedFetch ─────────────────────────────────────────────────

vi.mock("@/lib/api", () => {
  const fetchMock = vi.fn();
  return {
    API: "http://example.com",
    authenticatedFetch: fetchMock,
  };
});

// ── Import store and mock handle after mocks are in place ───────────────────

import { authenticatedFetch } from "@/lib/api";
import { useBrandingStore } from "@/state/branding";

const mockFetch = vi.mocked(authenticatedFetch);

beforeEach(() => {
  mockFetch.mockReset();
  // Reset the store to its initial state between tests.
  useBrandingStore.setState({
    initialized: false,
    brandingCompanyName: "DocReview360",
    brandingLogoUrl: null,
    brandingLogoAlt: "Organization logo",
    brandingSupportUrl: "/docs/",
    brandingDocsUrl: "/docs/",
    brandingSecurityUrl: "/security",
    brandingPrivacyUrl: "/privacy",
    brandingPrimaryColor: null,
    brandingAccentColor: null,
    brandingSidebarBg: null,
    brandingSidebarText: null,
    releaseVersion: "0.0.0-dev",
    releaseBuildNumber: "dev",
    releaseBuildDate: "unknown",
    releaseCommit: null,
    environment: "dev",
  });
});

// ── Source guard ─────────────────────────────────────────────────────────────

describe("state/branding.ts — source migration guard", () => {
  const REPO_ROOT = resolve(__dirname, "../..");
  const src = readFileSync(join(REPO_ROOT, "frontend/state/branding.ts"), "utf8");

  it("does not contain authenticatedFetch(`${API}/…`) — must use relative path", () => {
    expect(src).not.toMatch(/authenticatedFetch\s*\(\s*`\s*\$\{API\}\//);
  });

  it("does not contain raw fetch(`${API}/…`)", () => {
    expect(src).not.toMatch(/(?<![a-zA-Z])fetch\s*\(\s*`\s*\$\{API\}\//);
  });

  it("calls authenticatedFetch('/branding') with a relative path", () => {
    expect(src).toContain("authenticatedFetch('/branding')");
  });
});

// ── Store behavior ──────────────────────────────────────────────────────────

describe("useBrandingStore.initialize() — successful fetch", () => {
  const mockData = {
    branding_company_name: "ACME Corp",
    branding_logo_url: "https://acme.example.com/logo.png",
    branding_logo_alt: "ACME Logo",
    branding_support_url: "https://acme.example.com/support",
    branding_docs_url: "https://acme.example.com/docs",
    branding_security_url: "https://acme.example.com/security",
    branding_privacy_url: "https://acme.example.com/privacy",
    branding_primary_color: "#007bff",
    branding_accent_color: "#6c757d",
    branding_sidebar_bg: "#343a40",
    branding_sidebar_text: "#ffffff",
    release_version: "1.2.3",
    release_build_number: "456",
    release_build_date: "2026-03-12",
    release_commit: "abc1234",
    environment: "production",
  };

  beforeEach(() => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });
  });

  it("calls authenticatedFetch('/branding')", async () => {
    await useBrandingStore.getState().initialize();
    expect(mockFetch).toHaveBeenCalledOnce();
    expect(mockFetch).toHaveBeenCalledWith("/branding");
  });

  it("populates brandingCompanyName from the response", async () => {
    await useBrandingStore.getState().initialize();
    expect(useBrandingStore.getState().brandingCompanyName).toBe("ACME Corp");
  });

  it("populates brandingLogoUrl from the response", async () => {
    await useBrandingStore.getState().initialize();
    expect(useBrandingStore.getState().brandingLogoUrl).toBe(
      "https://acme.example.com/logo.png",
    );
  });

  it("populates color fields from the response", async () => {
    await useBrandingStore.getState().initialize();
    const state = useBrandingStore.getState();
    expect(state.brandingPrimaryColor).toBe("#007bff");
    expect(state.brandingAccentColor).toBe("#6c757d");
    expect(state.brandingSidebarBg).toBe("#343a40");
    expect(state.brandingSidebarText).toBe("#ffffff");
  });

  it("populates release metadata from the response", async () => {
    await useBrandingStore.getState().initialize();
    const state = useBrandingStore.getState();
    expect(state.releaseVersion).toBe("1.2.3");
    expect(state.releaseBuildNumber).toBe("456");
    expect(state.releaseBuildDate).toBe("2026-03-12");
    expect(state.releaseCommit).toBe("abc1234");
    expect(state.environment).toBe("production");
  });

  it("sets initialized to true after a successful fetch", async () => {
    expect(useBrandingStore.getState().initialized).toBe(false);
    await useBrandingStore.getState().initialize();
    expect(useBrandingStore.getState().initialized).toBe(true);
  });
});

describe("useBrandingStore.initialize() — idempotency", () => {
  it("does not re-fetch when called a second time without force=true", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ branding_company_name: "First" }),
    });
    await useBrandingStore.getState().initialize();
    await useBrandingStore.getState().initialize(); // second call, no force
    expect(mockFetch).toHaveBeenCalledOnce();
  });

  it("re-fetches when called with force=true", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ branding_company_name: "Updated" }),
    });
    await useBrandingStore.getState().initialize();
    await useBrandingStore.getState().initialize(true); // force refresh
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});

describe("useBrandingStore.initialize() — error handling", () => {
  it("uses default values when fetch returns non-ok status", async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await useBrandingStore.getState().initialize();
    const state = useBrandingStore.getState();
    expect(state.brandingCompanyName).toBe("DocReview360");
    expect(state.brandingLogoUrl).toBeNull();
    expect(state.initialized).toBe(true);
  });

  it("uses default values when fetch throws a network error", async () => {
    mockFetch.mockRejectedValue(new TypeError("Network failed"));
    await useBrandingStore.getState().initialize();
    const state = useBrandingStore.getState();
    expect(state.brandingCompanyName).toBe("DocReview360");
    expect(state.initialized).toBe(true);
  });

  it("does not throw when the fetch fails", async () => {
    mockFetch.mockRejectedValue(new Error("Unexpected"));
    await expect(useBrandingStore.getState().initialize()).resolves.toBeUndefined();
  });

  it("falls back to default for fields with empty string values", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          branding_company_name: "   ", // whitespace-only → use default
          branding_logo_url: "",         // empty → null
        }),
    });
    await useBrandingStore.getState().initialize();
    const state = useBrandingStore.getState();
    expect(state.brandingCompanyName).toBe("DocReview360"); // falls back
    expect(state.brandingLogoUrl).toBeNull();
  });
});
