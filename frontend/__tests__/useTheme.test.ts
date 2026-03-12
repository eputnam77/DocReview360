/**
 * Item 42 — useTheme CSS variable injection tests.
 *
 * Verifies that useTheme injects branding colors from useBrandingStore into
 * document.documentElement CSS custom properties, and removes them when
 * the color is null/cleared.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import React from "react";

// ── Mock the branding store ─────────────────────────────────────────────────
// We expose a mutable object so individual tests can update the state.
const mockBrandingState = {
  brandingPrimaryColor: null as string | null,
  brandingAccentColor: null as string | null,
  brandingSidebarBg: null as string | null,
  brandingSidebarText: null as string | null,
};

vi.mock("@/state/branding", () => ({
  useBrandingStore: (selector: (s: typeof mockBrandingState) => unknown) =>
    selector(mockBrandingState),
}));

import { useTheme } from "@/lib/useTheme";

// Track applied CSS properties for assertions.
const setProperty = vi.fn();
const removeProperty = vi.fn();

beforeEach(() => {
  setProperty.mockClear();
  removeProperty.mockClear();
  mockBrandingState.brandingPrimaryColor = null;
  mockBrandingState.brandingAccentColor = null;
  mockBrandingState.brandingSidebarBg = null;
  mockBrandingState.brandingSidebarText = null;

  // Spy on document.documentElement style methods.
  Object.defineProperty(document.documentElement, "style", {
    value: {
      setProperty,
      removeProperty,
    },
    writable: true,
    configurable: true,
  });
});

describe("useTheme — CSS variable injection", () => {
  it("sets --color-primary when brandingPrimaryColor is provided", () => {
    mockBrandingState.brandingPrimaryColor = "#007bff";
    renderHook(() => useTheme());
    expect(setProperty).toHaveBeenCalledWith("--color-primary", "#007bff");
  });

  it("removes --color-primary when brandingPrimaryColor is null", () => {
    mockBrandingState.brandingPrimaryColor = null;
    renderHook(() => useTheme());
    expect(removeProperty).toHaveBeenCalledWith("--color-primary");
  });

  it("sets --color-accent when brandingAccentColor is provided", () => {
    mockBrandingState.brandingAccentColor = "#6c757d";
    renderHook(() => useTheme());
    expect(setProperty).toHaveBeenCalledWith("--color-accent", "#6c757d");
  });

  it("removes --color-accent when brandingAccentColor is null", () => {
    mockBrandingState.brandingAccentColor = null;
    renderHook(() => useTheme());
    expect(removeProperty).toHaveBeenCalledWith("--color-accent");
  });

  it("sets --sidebar-bg when brandingSidebarBg is provided", () => {
    mockBrandingState.brandingSidebarBg = "#343a40";
    renderHook(() => useTheme());
    expect(setProperty).toHaveBeenCalledWith("--sidebar-bg", "#343a40");
  });

  it("removes --sidebar-bg when brandingSidebarBg is null", () => {
    mockBrandingState.brandingSidebarBg = null;
    renderHook(() => useTheme());
    expect(removeProperty).toHaveBeenCalledWith("--sidebar-bg");
  });

  it("sets --sidebar-text when brandingSidebarText is provided", () => {
    mockBrandingState.brandingSidebarText = "#ffffff";
    renderHook(() => useTheme());
    expect(setProperty).toHaveBeenCalledWith("--sidebar-text", "#ffffff");
  });

  it("removes --sidebar-text when brandingSidebarText is null", () => {
    mockBrandingState.brandingSidebarText = null;
    renderHook(() => useTheme());
    expect(removeProperty).toHaveBeenCalledWith("--sidebar-text");
  });

  it("sets all four properties when all branding colors are configured", () => {
    mockBrandingState.brandingPrimaryColor = "#111";
    mockBrandingState.brandingAccentColor = "#222";
    mockBrandingState.brandingSidebarBg = "#333";
    mockBrandingState.brandingSidebarText = "#444";
    renderHook(() => useTheme());
    expect(setProperty).toHaveBeenCalledWith("--color-primary", "#111");
    expect(setProperty).toHaveBeenCalledWith("--color-accent", "#222");
    expect(setProperty).toHaveBeenCalledWith("--sidebar-bg", "#333");
    expect(setProperty).toHaveBeenCalledWith("--sidebar-text", "#444");
    expect(removeProperty).not.toHaveBeenCalled();
  });

  it("removes all four properties when all colors are null (default state)", () => {
    renderHook(() => useTheme());
    expect(removeProperty).toHaveBeenCalledWith("--color-primary");
    expect(removeProperty).toHaveBeenCalledWith("--color-accent");
    expect(removeProperty).toHaveBeenCalledWith("--sidebar-bg");
    expect(removeProperty).toHaveBeenCalledWith("--sidebar-text");
    expect(setProperty).not.toHaveBeenCalled();
  });
});
