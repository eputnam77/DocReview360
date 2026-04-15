const DEFAULT_API_ORIGINS = [
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];
const SAME_HOST_API_FALLBACKS = [
  // authenticatedFetch() falls back to the current browser host on port 8000.
  // Allow that zero-config dev path even when the app is opened via a machine
  // hostname instead of localhost.
  "http://*:8000",
  "https://*:8000",
];

function normalizeOrigin(value) {
  if (!value || typeof value !== "string") {
    return null;
  }

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function buildConnectSrc() {
  const sources = new Set(["'self'", "ws:", "wss:", ...SAME_HOST_API_FALLBACKS]);
  for (const value of [
    process.env.NEXT_PUBLIC_API_BASE,
    process.env.DOCREVIEW360_API_BASE,
    ...DEFAULT_API_ORIGINS,
  ]) {
    const origin = normalizeOrigin(value);
    if (origin) {
      sources.add(origin);
    }
  }
  return Array.from(sources).join(" ");
}

function buildFrameSrc() {
  const sources = new Set(["'self'"]);
  for (const value of [
    process.env.NEXT_PUBLIC_FSV_FRONTEND_URL,
    process.env.DOCREVIEW360_FSV_FRONTEND_URL,
  ]) {
    const origin = normalizeOrigin(value);
    if (origin) {
      sources.add(origin);
    }
  }
  return Array.from(sources).join(" ");
}

const connectSrc = buildConnectSrc();
const frameSrc = buildFrameSrc();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { optimizeCss: true },
  distDir: process.env.NEXT_DIST_DIR || ".next",
  outputFileTracingExcludes: {
    "/api/tools/checker": ["next.config.js"],
  },
  i18n: {
    locales: ["en", "es", "fr", "de"],
    defaultLocale: "en",
    localeDetection: false,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              "font-src 'self'",
              `connect-src ${connectSrc}`,
              `frame-src ${frameSrc}`,
              "frame-ancestors 'none'",
            ].join("; "),
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
