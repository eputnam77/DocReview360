// Use the configured backend URL when provided; otherwise, default to the
// local development API server.
const envBase = process.env.NEXT_PUBLIC_API_BASE?.trim();
const RUNTIME_API_BASE_KEY = "docreview360_api_base";

function _runtimeBase(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const fromWindow = (window as { __DOCREVIEW360_API_BASE?: unknown }).__DOCREVIEW360_API_BASE;
  if (typeof fromWindow === "string" && fromWindow.trim()) {
    return fromWindow.trim();
  }
  const fromStorage = window.localStorage.getItem(RUNTIME_API_BASE_KEY);
  return fromStorage && fromStorage.trim() ? fromStorage.trim() : null;
}

export const API =
  _runtimeBase() ??
  (envBase && envBase.length > 0
    ? envBase
    : typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : "http://localhost:8000");

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

  // Prepend API base URL to relative URLs
  let fullUrl = url;
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    // Ensure the API base URL doesn't have a trailing slash and the path starts with a slash
    const baseUrl = API.endsWith('/') ? API.slice(0, -1) : API;
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
    console.error(`Failed to fetch ${fullUrl}:`, error);
    throw error;
  }
}
