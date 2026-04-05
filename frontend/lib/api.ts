// Use the configured backend URL when provided; otherwise, default to the
// local development API server.
const envBase = process.env.NEXT_PUBLIC_API_BASE?.trim();
const RUNTIME_API_BASE_KEY = "docreview360_api_base";

function _windowRuntimeBase(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const fromWindow = (window as { __DOCREVIEW360_API_BASE?: unknown }).__DOCREVIEW360_API_BASE;
  if (typeof fromWindow === "string" && fromWindow.trim()) {
    return fromWindow.trim();
  }
  return null;
}

function _storageRuntimeBase(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const fromStorage = window.localStorage.getItem(RUNTIME_API_BASE_KEY);
  return fromStorage && fromStorage.trim() ? fromStorage.trim() : null;
}

export const API =
  _windowRuntimeBase() ??
  (envBase && envBase.length > 0
    ? envBase
    : _storageRuntimeBase() ??
      (typeof window !== "undefined"
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : "http://localhost:8000"));

function _resolveApiBase(): string {
  return (
    _windowRuntimeBase() ??
    (envBase && envBase.length > 0
      ? envBase
      : _storageRuntimeBase() ??
        (typeof window !== "undefined"
          ? `${window.location.protocol}//${window.location.hostname}:8000`
          : "http://localhost:8000"))
  );
}

function _readCookie(name: string): string | null {
  if (typeof document === "undefined" || !document.cookie) {
    return null;
  }
  const prefix = `${name}=`;
  for (const cookie of document.cookie.split(";")) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

// JWT is stored in memory only — never in localStorage or sessionStorage.
// This prevents XSS-based token theft: a cross-site script injected into the
// page cannot exfiltrate a token it cannot reach via the DOM or Storage APIs.
// The backend sets an httpOnly cookie on /token so authenticated requests work
// across page refreshes even when _memoryToken is null.
let _memoryToken: string | null = null;

export function getStoredAccessToken(): string | null {
  return _memoryToken;
}

export function setStoredAccessToken(token: string): void {
  _memoryToken = token;
}

export function clearStoredAccessToken(): void {
  _memoryToken = null;
}

export function getCsrfToken(): string | null {
  return _readCookie("csrf_token");
}

// Utility function for authenticated API calls
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers);
  const storedToken = getStoredAccessToken();
  if (storedToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${storedToken}`);
  }
  const csrfToken = getCsrfToken();
  if (csrfToken && !headers.has("X-CSRF-Token")) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  // Prepend API base URL to relative URLs
  let fullUrl = url;
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    // Ensure the API base URL doesn't have a trailing slash and the path starts with a slash
    const base = _resolveApiBase();
    const baseUrl = base.endsWith('/') ? base.slice(0, -1) : base;
    const path = url.startsWith('/') ? url : `/${url}`;
    fullUrl = `${baseUrl}${path}`;
  }

  try {
    return await fetch(fullUrl, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (error) {
    // Network-level failures (backend down, DNS error, connection refused)
    // return a synthetic 503 instead of throwing.  Every caller already
    // checks `res.ok`, so they handle this gracefully — and no uncaught
    // TypeError crashes the page.
    console.error(`Network error fetching ${fullUrl}:`, error);
    return new Response(
      JSON.stringify({ detail: "Network error: unable to reach the API server" }),
      { status: 503, statusText: "Service Unavailable", headers: { "Content-Type": "application/json" } },
    );
  }
}
