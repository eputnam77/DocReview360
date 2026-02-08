import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { authenticatedFetch } from "@/lib/api";

describe("authenticatedFetch auth headers", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    localStorage.clear();
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 200 })) as typeof fetch;
  });

  afterEach(() => {
    localStorage.clear();
    if (originalFetch) {
      global.fetch = originalFetch;
    }
  });

  it("adds bearer auth from stored access token", async () => {
    localStorage.setItem("access_token", "token-123");

    await authenticatedFetch("http://example.test/projects", { method: "POST" });

    const [, options] = vi.mocked(global.fetch).mock.calls[0];
    const headers = new Headers(options?.headers);
    expect(headers.get("Authorization")).toBe("Bearer token-123");
    expect(options?.credentials).toBe("include");
  });

  it("does not overwrite an explicit authorization header", async () => {
    localStorage.setItem("access_token", "token-123");

    await authenticatedFetch("http://example.test/projects", {
      headers: { Authorization: "Bearer explicit-token" },
    });

    const [, options] = vi.mocked(global.fetch).mock.calls[0];
    const headers = new Headers(options?.headers);
    expect(headers.get("Authorization")).toBe("Bearer explicit-token");
  });
});
