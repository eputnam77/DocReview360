"use client";

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

function FsvFrontendUnavailable() {
  return (
    <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-slate-50 px-6 py-10">
      <div className="w-full max-w-xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">
          Federal Style Validator
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
          FSV frontend is not configured
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          Set <code>NEXT_PUBLIC_FSV_FRONTEND_URL</code> to the standalone FSV frontend so this
          page can render the same interface users see in the dedicated FSV app.
        </p>
      </div>
    </main>
  );
}

export default function DocumentQualityPage() {
  const frontendUrl = resolveFsvFrontendUrl();

  if (!frontendUrl) {
    return <FsvFrontendUnavailable />;
  }

  return (
    <main className="h-[calc(100vh-4rem)] overflow-hidden bg-slate-50">
      <iframe
        title="Federal Style Validator"
        src={frontendUrl}
        className="block h-full w-full border-0 bg-white"
        referrerPolicy="strict-origin-when-cross-origin"
      />
    </main>
  );
}
