/**
 * Integration test: verifies that all API calls constructed by authenticatedFetch
 * resolve against the NEXT_PUBLIC_API_BASE environment variable when set.
 *
 * This satisfies RELEASE_CHECKLIST.md Item 5:
 * "Add a frontend integration test that sets NEXT_PUBLIC_API_BASE to a custom
 *  origin and verifies that all API calls resolve against that base."
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const CUSTOM_BASE = 'https://api.example.com';

describe('API base URL resolution', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('uses NEXT_PUBLIC_API_BASE when set', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE', CUSTOM_BASE);

    const { API } = await import('../lib/api');
    expect(API).toBe(CUSTOM_BASE);
  });

  it('authenticatedFetch prepends NEXT_PUBLIC_API_BASE to relative paths', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE', CUSTOM_BASE);

    let capturedUrl: string | undefined;
    vi.stubGlobal('fetch', (url: string) => {
      capturedUrl = url;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
        headers: new Headers(),
      } as Response);
    });

    const { authenticatedFetch } = await import('../lib/api');
    await authenticatedFetch('/templates');

    expect(capturedUrl).toBe(`${CUSTOM_BASE}/templates`);
  });

  it('authenticatedFetch prepends custom base with trailing slash stripped', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE', `${CUSTOM_BASE}/`);

    let capturedUrl: string | undefined;
    vi.stubGlobal('fetch', (url: string) => {
      capturedUrl = url;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
        headers: new Headers(),
      } as Response);
    });

    const { authenticatedFetch } = await import('../lib/api');
    await authenticatedFetch('/projects');

    // Trailing slash on base should be stripped so we don't get double-slash.
    expect(capturedUrl).toBe(`${CUSTOM_BASE}/projects`);
  });

  it('authenticatedFetch does not modify already-absolute URLs', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE', CUSTOM_BASE);

    const absoluteUrl = 'https://other.example.com/resource';
    let capturedUrl: string | undefined;
    vi.stubGlobal('fetch', (url: string) => {
      capturedUrl = url;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
        headers: new Headers(),
      } as Response);
    });

    const { authenticatedFetch } = await import('../lib/api');
    await authenticatedFetch(absoluteUrl);

    expect(capturedUrl).toBe(absoluteUrl);
  });

  it('falls back to localhost:8000 when NEXT_PUBLIC_API_BASE is not set', async () => {
    // Ensure env var is absent
    vi.unstubAllEnvs();

    // Provide a window.location stub without hostname-based magic to keep it simple.
    // In jsdom, location.hostname defaults to 'localhost'.
    const { API } = await import('../lib/api');
    // The fallback uses window.location.protocol + hostname + :8000 in a browser
    // context. In jsdom, window exists, so we accept either the jsdom-based value
    // or a plain localhost URL.
    expect(API).toMatch(/localhost:8000/);
  });
});
