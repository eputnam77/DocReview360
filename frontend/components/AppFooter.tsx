import { useEffect } from "react";

import { useBrandingStore } from "@/state/branding";

function shortCommit(commit: string | null): string | null {
  if (!commit) {
    return null;
  }
  return commit.length > 10 ? commit.slice(0, 10) : commit;
}

export default function AppFooter() {
  const initialize = useBrandingStore((s) => s.initialize);
  const brandingCompanyName = useBrandingStore((s) => s.brandingCompanyName);
  const brandingSupportUrl = useBrandingStore((s) => s.brandingSupportUrl);
  const brandingDocsUrl = useBrandingStore((s) => s.brandingDocsUrl);
  const brandingSecurityUrl = useBrandingStore((s) => s.brandingSecurityUrl);
  const brandingPrivacyUrl = useBrandingStore((s) => s.brandingPrivacyUrl);
  const releaseVersion = useBrandingStore((s) => s.releaseVersion);
  const releaseBuildNumber = useBrandingStore((s) => s.releaseBuildNumber);
  const releaseBuildDate = useBrandingStore((s) => s.releaseBuildDate);
  const releaseCommit = useBrandingStore((s) => s.releaseCommit);
  const environment = useBrandingStore((s) => s.environment);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const commitLabel = shortCommit(releaseCommit);

  return (
    <footer className="border-t border-border bg-background px-6 py-3 text-xs text-muted-foreground">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <p>
          {brandingCompanyName} | Release {releaseVersion} | Build {releaseBuildNumber} | Date {releaseBuildDate} | Env {environment}
          {commitLabel ? ` | Commit ${commitLabel}` : ""}
        </p>
        <div className="flex flex-wrap gap-3">
          <a className="underline" href={brandingSupportUrl}>Support</a>
          <a className="underline" href={brandingDocsUrl}>Docs</a>
          <a className="underline" href={brandingSecurityUrl}>Security</a>
          <a className="underline" href={brandingPrivacyUrl}>Privacy</a>
        </div>
      </div>
    </footer>
  );
}
