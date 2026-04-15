"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertCircle, ExternalLink, Loader2, Shield } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { authenticatedFetch } from "@/lib/api";
import { useUserStore } from "@/state/user";

type FsvStatusPayload = {
  configured?: boolean;
  reachable?: boolean;
  url?: string | null;
};

type BackendStatus = "checking" | "ready" | "unconfigured" | "unreachable";

export function normalizeExternalUrl(value: string | null | undefined): string | null {
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }

  try {
    const url = new URL(value.trim());
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    const normalized = url.toString();
    return normalized.endsWith("/") ? normalized.slice(0, -1) : normalized;
  } catch {
    return null;
  }
}

export function resolveFsvFrontendUrl(): string | null {
  return normalizeExternalUrl(process.env.NEXT_PUBLIC_FSV_FRONTEND_URL);
}

const FSV_FRONTEND_URL = resolveFsvFrontendUrl();

function StatusBanner({
  status,
  message,
}: {
  status: BackendStatus;
  message: string;
}) {
  const palette =
    status === "ready"
      ? {
          card: "border-green-200 bg-green-50",
          title: "text-green-900",
          body: "text-green-800",
        }
      : status === "checking"
        ? {
            card: "border-slate-200 bg-slate-50",
            title: "text-slate-900",
            body: "text-slate-700",
          }
        : {
            card: "border-amber-200 bg-amber-50",
            title: "text-amber-900",
            body: "text-amber-800",
          };

  return (
    <Card className={palette.card}>
      <CardContent className="pt-6">
        <div className="flex items-start gap-3">
          {status === "checking" ? (
            <Loader2 className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-slate-600" />
          ) : (
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          )}
          <div className="space-y-1">
            <p className={`text-sm font-semibold ${palette.title}`}>
              {status === "ready"
                ? "Connected to Federal Style Validator backend"
                : status === "checking"
                  ? "Checking Federal Style Validator backend"
                  : status === "unconfigured"
                    ? "Federal Style Validator backend is not configured"
                    : "Federal Style Validator backend is unreachable"}
            </p>
            <p className={`text-sm ${palette.body}`}>{message}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SetupCard() {
  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle>Configure the embedded Federal Style Validator frontend</CardTitle>
        <CardDescription>
          Set <code>NEXT_PUBLIC_FSV_FRONTEND_URL</code> so DocReview360 can host the standalone
          FSV UI instead of duplicating its validation features.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-slate-700">
        <p>
          The Federal Style Validator repo is available at <code>C:\dev\FedStyleValidator</code>.
          Run its backend and frontend separately, then point DocReview360 at the frontend URL.
        </p>
        <div className="space-y-2">
          <p className="font-medium text-slate-900">Suggested local setup</p>
          <pre className="overflow-x-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
{`cd C:\\dev\\FedStyleValidator
python run.py --mode ui --port 8000

cd C:\\dev\\FedStyleValidator\\frontend\\fedstylevalidator
npm install
npm run dev -- --host 127.0.0.1 --port 3001`}
          </pre>
        </div>
        <div className="space-y-2">
          <p className="font-medium text-slate-900">DocReview360 frontend env</p>
          <pre className="overflow-x-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
{`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
NEXT_PUBLIC_FSV_FRONTEND_URL=http://127.0.0.1:3001`}
          </pre>
        </div>
        <p>
          The backend health check on <code>/fsv/status</code> should also report the Federal Style
          Validator service as reachable before relying on this page.
        </p>
      </CardContent>
    </Card>
  );
}

export default function DocumentQualityPage() {
  const isAdmin = useUserStore((state) => state.isAdmin);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [statusMessage, setStatusMessage] = useState("Loading backend status...");

  useEffect(() => {
    let cancelled = false;

    async function loadStatus() {
      setBackendStatus("checking");
      setStatusMessage("Loading backend status...");

      try {
        const response = await authenticatedFetch("/fsv/status");
        if (!response.ok) {
          if (!cancelled) {
            setBackendStatus("unreachable");
            setStatusMessage(
              `DocReview360 could not verify the Federal Style Validator backend (${response.status} ${response.statusText}).`,
            );
          }
          return;
        }

        const payload = (await response.json()) as FsvStatusPayload;
        if (!payload.configured) {
          if (!cancelled) {
            setBackendStatus("unconfigured");
            setStatusMessage(
              "Configure the Federal Style Validator service URL in Tools before relying on backend status checks.",
            );
          }
          return;
        }

        if (!payload.reachable) {
          if (!cancelled) {
            setBackendStatus("unreachable");
            setStatusMessage(
              payload.url
                ? `Configured backend ${payload.url} did not respond to the health probe.`
                : "The configured Federal Style Validator backend did not respond to the health probe.",
            );
          }
          return;
        }

        if (!cancelled) {
          setBackendStatus("ready");
          setStatusMessage(
            payload.url
              ? `Health checks passed for ${payload.url}.`
              : "Health checks passed for the configured Federal Style Validator backend.",
          );
        }
      } catch {
        if (!cancelled) {
          setBackendStatus("unreachable");
          setStatusMessage("DocReview360 could not verify the Federal Style Validator backend.");
        }
      }
    }

    void loadStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Document Quality Checker</h1>
          <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
            <Shield className="h-3.5 w-3.5" />
            Powered by Federal Style Validator
          </span>
        </div>
        <p className="max-w-3xl text-sm text-slate-600">
          This page now hosts the Federal Style Validator frontend directly. DocReview360 no longer
          duplicates FSV validation controls or findings UI here.
        </p>
        {isAdmin ? (
          <Link href="/tools" className="text-sm font-medium text-slate-700 underline underline-offset-4">
            Back to Tools configuration
          </Link>
        ) : null}
      </div>

      <StatusBanner status={backendStatus} message={statusMessage} />

      {FSV_FRONTEND_URL ? (
        <Card>
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <CardTitle>Federal Style Validator</CardTitle>
              <CardDescription>
                Embedded from <code>{FSV_FRONTEND_URL}</code>
              </CardDescription>
            </div>
            <Link
              href={FSV_FRONTEND_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-300 px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <ExternalLink className="h-4 w-4" />
              Open in new tab
            </Link>
          </CardHeader>
          <CardContent>
            <iframe
              title="Federal Style Validator"
              src={FSV_FRONTEND_URL}
              className="h-[78vh] w-full rounded-xl border border-slate-200 bg-white"
              referrerPolicy="strict-origin-when-cross-origin"
            />
          </CardContent>
        </Card>
      ) : (
        <SetupCard />
      )}
    </div>
  );
}
