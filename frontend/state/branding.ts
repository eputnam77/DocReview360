import { create } from "zustand";

import { authenticatedFetch } from "@/lib/api";

/**
 * DR-FSV-1: Canonical brand tokens from FedStyleValidator (brand-tokens.json v1.0.0).
 * DocReview360 reads these when rendering the FSV add-in surface so colors stay
 * in sync as FSV's design evolves, instead of hardcoding hex values everywhere.
 */
export const FSV_BRAND_TOKENS = {
  version: "1.0.0",
  primaryColor: "#4F46E5",   // Indigo-600 — primary action, aligned with DocReview360
  primaryHover: "#4338CA",   // Indigo-700
  severityError: "#EF4444",  // red-500 — error indicators
  severityWarning: "#F59E0B", // amber-500 — warning indicators
  severityInfo: "#0EA5E9",   // sky-500 — info indicators
  severitySuccess: "#22C55E", // green-500 — success/pass indicators
} as const;

interface BrandingState {
  brandingCompanyName: string;
  brandingLogoUrl: string | null;
  brandingLogoAlt: string;
  brandingSupportUrl: string;
  brandingDocsUrl: string;
  brandingSecurityUrl: string;
  brandingPrivacyUrl: string;
  brandingPrimaryColor: string | null;
  brandingAccentColor: string | null;
  brandingSidebarBg: string | null;
  brandingSidebarText: string | null;
  /** DR-FSV-1: Primary color for FSV add-in surfaces. Falls back to FSV_BRAND_TOKENS.primaryColor when no org override is set. */
  fsvPrimaryColor: string;
  releaseVersion: string;
  releaseBuildNumber: string;
  releaseBuildDate: string;
  releaseCommit: string | null;
  environment: string;
  initialized: boolean;
  initialize: (force?: boolean) => Promise<void>;
}

const DEFAULTS = {
  brandingCompanyName: "DocReview360",
  brandingLogoUrl: null as string | null,
  brandingLogoAlt: "Organization logo",
  brandingSupportUrl: "/docs/",
  brandingDocsUrl: "/docs/",
  brandingSecurityUrl: "/security",
  brandingPrivacyUrl: "/privacy",
  brandingPrimaryColor: null as string | null,
  brandingAccentColor: null as string | null,
  brandingSidebarBg: null as string | null,
  brandingSidebarText: null as string | null,
  fsvPrimaryColor: FSV_BRAND_TOKENS.primaryColor,
  releaseVersion: "0.0.0-dev",
  releaseBuildNumber: "dev",
  releaseBuildDate: "unknown",
  releaseCommit: null as string | null,
  environment: "dev",
};

export const useBrandingStore = create<BrandingState>((set, get) => ({
  ...DEFAULTS,
  initialized: false,
  async initialize(force = false) {
    if (get().initialized && !force) {
      return;
    }

    try {
      const resp = await authenticatedFetch('/branding');
      if (!resp.ok) {
        set({ ...DEFAULTS, initialized: true });
        return;
      }
      const data = (await resp.json()) as Record<string, unknown>;
      set({
        brandingCompanyName:
          typeof data.branding_company_name === "string" && data.branding_company_name.trim()
            ? data.branding_company_name.trim()
            : DEFAULTS.brandingCompanyName,
        brandingLogoUrl:
          typeof data.branding_logo_url === "string" && data.branding_logo_url.trim()
            ? data.branding_logo_url.trim()
            : null,
        brandingLogoAlt:
          typeof data.branding_logo_alt === "string" && data.branding_logo_alt.trim()
            ? data.branding_logo_alt.trim()
            : DEFAULTS.brandingLogoAlt,
        brandingSupportUrl:
          typeof data.branding_support_url === "string" && data.branding_support_url.trim()
            ? data.branding_support_url.trim()
            : DEFAULTS.brandingSupportUrl,
        brandingDocsUrl:
          typeof data.branding_docs_url === "string" && data.branding_docs_url.trim()
            ? data.branding_docs_url.trim()
            : DEFAULTS.brandingDocsUrl,
        brandingSecurityUrl:
          typeof data.branding_security_url === "string" && data.branding_security_url.trim()
            ? data.branding_security_url.trim()
            : DEFAULTS.brandingSecurityUrl,
        brandingPrivacyUrl:
          typeof data.branding_privacy_url === "string" && data.branding_privacy_url.trim()
            ? data.branding_privacy_url.trim()
            : DEFAULTS.brandingPrivacyUrl,
        brandingPrimaryColor:
          typeof data.branding_primary_color === "string" && data.branding_primary_color.trim()
            ? data.branding_primary_color.trim()
            : null,
        brandingAccentColor:
          typeof data.branding_accent_color === "string" && data.branding_accent_color.trim()
            ? data.branding_accent_color.trim()
            : null,
        brandingSidebarBg:
          typeof data.branding_sidebar_bg === "string" && data.branding_sidebar_bg.trim()
            ? data.branding_sidebar_bg.trim()
            : null,
        brandingSidebarText:
          typeof data.branding_sidebar_text === "string" && data.branding_sidebar_text.trim()
            ? data.branding_sidebar_text.trim()
            : null,
        // DR-FSV-1: org override falls back to canonical FSV token
        fsvPrimaryColor:
          typeof data.branding_primary_color === "string" && data.branding_primary_color.trim()
            ? data.branding_primary_color.trim()
            : FSV_BRAND_TOKENS.primaryColor,
        releaseVersion:
          typeof data.release_version === "string" && data.release_version.trim()
            ? data.release_version.trim()
            : DEFAULTS.releaseVersion,
        releaseBuildNumber:
          typeof data.release_build_number === "string" && data.release_build_number.trim()
            ? data.release_build_number.trim()
            : DEFAULTS.releaseBuildNumber,
        releaseBuildDate:
          typeof data.release_build_date === "string" && data.release_build_date.trim()
            ? data.release_build_date.trim()
            : DEFAULTS.releaseBuildDate,
        releaseCommit:
          typeof data.release_commit === "string" && data.release_commit.trim()
            ? data.release_commit.trim()
            : null,
        environment:
          typeof data.environment === "string" && data.environment.trim()
            ? data.environment.trim()
            : DEFAULTS.environment,
        initialized: true,
      });
    } catch {
      set({ ...DEFAULTS, initialized: true });
    }
  },
}));
