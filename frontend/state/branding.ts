import { create } from "zustand";

import { API } from "@/lib/api";

interface BrandingState {
  brandingCompanyName: string;
  brandingLogoUrl: string | null;
  brandingLogoAlt: string;
  brandingSupportUrl: string;
  brandingDocsUrl: string;
  brandingSecurityUrl: string;
  brandingPrivacyUrl: string;
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
      const resp = await fetch(`${API}/branding`);
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
