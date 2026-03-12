import { afterEach, describe, expect, it, vi } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

async function getCspValue(): Promise<string> {
  vi.resetModules();
  const configPath = require.resolve("../next.config.js");
  delete require.cache[configPath];
  const nextConfig = require(configPath);
  const headers = await nextConfig.headers();
  const cspHeader = headers[0]?.headers.find(
    (header: { key: string; value: string }) => header.key === "Content-Security-Policy",
  );
  return cspHeader?.value ?? "";
}

describe("next.config CSP connect-src", () => {
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
  });
});
