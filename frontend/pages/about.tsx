import React, { useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkle, Tag, CalendarDays, GitBranch, Globe, Shield, ExternalLink } from "lucide-react";
import { useBrandingStore } from "@/state/branding";

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-border last:border-none">
      <span className="mt-0.5 flex-shrink-0 text-muted-foreground">{icon}</span>
      <div className="flex flex-col sm:flex-row sm:gap-4 flex-1 min-w-0">
        <span className="w-32 flex-shrink-0 text-sm font-medium text-muted-foreground">
          {label}
        </span>
        <span className="text-sm text-foreground break-all">{value}</span>
      </div>
    </div>
  );
}

export default function AboutPage() {
  const initializeBranding = useBrandingStore((s) => s.initialize);
  const brandingCompanyName = useBrandingStore((s) => s.brandingCompanyName);
  const releaseVersion = useBrandingStore((s) => s.releaseVersion);
  const releaseBuildNumber = useBrandingStore((s) => s.releaseBuildNumber);
  const releaseBuildDate = useBrandingStore((s) => s.releaseBuildDate);
  const releaseCommit = useBrandingStore((s) => s.releaseCommit);
  const environment = useBrandingStore((s) => s.environment);

  useEffect(() => {
    void initializeBranding();
  }, [initializeBranding]);

  const appName = brandingCompanyName || "DocReview360";

  return (
    <div className="p-8 max-w-2xl space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkle className="w-6 h-6 text-purple-600" />
          About {appName}
        </h1>
        <p className="text-sm text-muted-foreground">
          Build information, license, and project links.
        </p>
      </div>

      {/* App description */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Overview</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground leading-relaxed space-y-2">
          <p>
            <strong className="text-foreground">{appName}</strong> is a modern, collaborative
            document workflow and approval platform. It is designed to streamline regulatory,
            policy, and technical documentation review cycles for teams of any size, with
            full audit history, role-based access control, and a flexible phase-based workflow
            engine.
          </p>
          <p>
            Built with FastAPI, SQLAlchemy, Next.js, and React. Open-source under the MIT
            License.
          </p>
        </CardContent>
      </Card>

      {/* Version info */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Version Information</CardTitle>
        </CardHeader>
        <CardContent className="py-0">
          <InfoRow
            icon={<Tag className="w-4 h-4" />}
            label="Version"
            value={releaseVersion}
          />
          <InfoRow
            icon={<CalendarDays className="w-4 h-4" />}
            label="Build date"
            value={releaseBuildDate}
          />
          <InfoRow
            icon={<Tag className="w-4 h-4" />}
            label="Build number"
            value={releaseBuildNumber}
          />
          {releaseCommit && (
            <InfoRow
              icon={<GitBranch className="w-4 h-4" />}
              label="Commit"
              value={
                <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                  {releaseCommit}
                </span>
              }
            />
          )}
          <InfoRow
            icon={<Globe className="w-4 h-4" />}
            label="Environment"
            value={
              <span
                className={
                  environment === "production"
                    ? "text-emerald-700 font-medium"
                    : "text-amber-700 font-medium"
                }
              >
                {environment}
              </span>
            }
          />
        </CardContent>
      </Card>

      {/* License */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Shield className="w-4 h-4 text-indigo-600" />
            License
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            {appName} is released under the{" "}
            <strong className="text-foreground">MIT License</strong>. You are free to use,
            modify, and distribute this software in accordance with the terms of the license.
          </p>
          <p>
            Copyright &copy; {new Date().getFullYear()} {appName} contributors.
          </p>
        </CardContent>
      </Card>

      {/* Links */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Links</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-col gap-2">
            <a
              href="https://github.com/docreview360/docreview360"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:underline"
            >
              GitHub Repository
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <Link
              href="/help"
              className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:underline"
            >
              Help &amp; Documentation
            </Link>
            <Link
              href="/api-docs"
              className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:underline"
            >
              API Reference
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
