import React from "react";

const DEFAULT_DOCS_URL = "https://eputnam77.github.io/DocReview360/";

export default function DocsPage() {
  const docsUrl = process.env.NEXT_PUBLIC_DOCS_URL ?? DEFAULT_DOCS_URL;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-screen-xl px-5 py-6">
        <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Documentation</h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-500">
                The hosted documentation is embedded below. If it does not load in this
                environment, use the in-app help center or open the docs in a new tab.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <a
                href="/help"
                className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
              >
                In-app help
              </a>
              <a
                href={docsUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700"
              >
                Open docs
              </a>
            </div>
          </div>
        </div>
        <iframe
          src={docsUrl}
          title="Documentation"
          className="h-[calc(100vh-11rem)] w-full rounded-2xl border border-slate-200 bg-white"
        />
      </div>
    </div>
  );
}
