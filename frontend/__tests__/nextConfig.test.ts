import { afterEach, describe, expect, it, vi } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

async function getCspValue(): Promise<string> {
  const nextConfig = getNextConfig();
  const headers = await nextConfig.headers();
  const cspHeader = headers[0]?.headers.find(
    (header: { key: string; value: string }) => header.key === "Content-Security-Policy",
  );
  return cspHeader?.value ?? "";
}

function getNextConfig() {
  vi.resetModules();
  const configPath = require.resolve("../next.config.js");
  delete require.cache[configPath];
  return require(configPath);
}

describe("next.config headers", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("allows the configured API origin and local dev fallback origins", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE", "https://api.example.com/v1");

    const csp = await getCspValue();

    expect(csp).toContain("connect-src 'self' ws: wss:");
    expect(csp).toContain("https://api.example.com");
    expect(csp).toContain("http://localhost:8000");
    expect(csp).toContain("http://127.0.0.1:8000");
    expect(csp).toContain("http://*:8000");
    expect(csp).toContain("https://*:8000");
  });

  it("allows the configured FSV frontend in frame-src", async () => {
    vi.stubEnv("NEXT_PUBLIC_FSV_FRONTEND_URL", "https://fsv.example.com/embed");

    const csp = await getCspValue();

    expect(csp).toContain("frame-src 'self' https://fsv.example.com");
  });

  it("disables localeDetection for Next.js 16 compatibility", async () => {
    const nextConfig = getNextConfig();

    expect(nextConfig.i18n?.localeDetection).toBe(false);
  });

  it("excludes next.config.js from the checker API route trace", () => {
    const nextConfig = getNextConfig();

    expect(nextConfig.outputFileTracingExcludes).toMatchObject({
      "/api/tools/checker": ["next.config.js"],
    });
  });
});
