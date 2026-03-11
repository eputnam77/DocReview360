// SPDX-License-Identifier: MIT
/**
 * useTheme — injects branding color CSS custom properties into :root whenever
 * the org-level theme colors change in the branding store.
 *
 * Callers simply invoke the hook at component top level; no return value is
 * needed.  The properties land on `document.documentElement` so every CSS
 * rule that references `var(--color-primary)`, `var(--color-accent)`,
 * `var(--sidebar-bg)`, or `var(--sidebar-text)` picks them up automatically.
 */
import { useEffect } from "react";

import { useBrandingStore } from "@/state/branding";

export function useTheme(): void {
  const primaryColor = useBrandingStore((s) => s.brandingPrimaryColor);
  const accentColor = useBrandingStore((s) => s.brandingAccentColor);
  const sidebarBg = useBrandingStore((s) => s.brandingSidebarBg);
  const sidebarText = useBrandingStore((s) => s.brandingSidebarText);

  useEffect(() => {
    const root = document.documentElement;

    if (primaryColor) {
      root.style.setProperty("--color-primary", primaryColor);
    } else {
      root.style.removeProperty("--color-primary");
    }

    if (accentColor) {
      root.style.setProperty("--color-accent", accentColor);
    } else {
      root.style.removeProperty("--color-accent");
    }

    if (sidebarBg) {
      root.style.setProperty("--sidebar-bg", sidebarBg);
    } else {
      root.style.removeProperty("--sidebar-bg");
    }

    if (sidebarText) {
      root.style.setProperty("--sidebar-text", sidebarText);
    } else {
      root.style.removeProperty("--sidebar-text");
    }
  }, [primaryColor, accentColor, sidebarBg, sidebarText]);
}
