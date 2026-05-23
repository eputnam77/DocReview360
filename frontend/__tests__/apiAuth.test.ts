import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import {
  authenticatedFetch,
  clearStoredAccessToken,
  setStoredAccessToken,
} from "@/lib/api";

describe("authenticatedFetch auth headers", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    clearStoredAccessToken();
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 200 })) as typeof fetch;
  });

  afterEach(() => {
    clearStoredAccessToken();
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
    if (originalFetch) {
      global.fetch = originalFetch;
    }
  });

  it("adds bearer auth from stored access token", async () => {
    setStoredAccessToken("token-123");

    await authenticatedFetch("http://example.test/projects", { method: "POST" });

    const [, options] = vi.mocked(global.fetch).mock.calls[0];
    const headers = new Headers(options?.headers);
    expect(headers.get("Authorization")).toBe("Bearer token-123");
    expect(options?.credentials).toBe("include");
  });

  it("does not overwrite an explicit authorization header", async () => {
    setStoredAccessToken("token-123");

    await authenticatedFetch("http://example.test/projects", {
      headers: { Authorization: "Bearer explicit-token" },
    });

    const [, options] = vi.mocked(global.fetch).mock.calls[0];
    const headers = new Headers(options?.headers);
    expect(headers.get("Authorization")).toBe("Bearer explicit-token");
  });

  it("adds X-CSRF-Token from the csrf cookie", async () => {
    document.cookie = "csrf_token=csrf-123; path=/";

    await authenticatedFetch("http://example.test/projects");

    const [, options] = vi.mocked(global.fetch).mock.calls[0];
    const headers = new Headers(options?.headers);
    expect(headers.get("X-CSRF-Token")).toBe("csrf-123");
  });

  it("returns a synthetic 503 response when fetch rejects", async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    const response = await authenticatedFetch("/projects");

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Network error: unable to reach the API server",
    });
    expect(errorSpy).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("Network error fetching"),
    );
    errorSpy.mockRestore();
    warnSpy.mockRestore();
  });
});
