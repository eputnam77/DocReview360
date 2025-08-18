// Use the configured backend URL when provided; otherwise, default to the
// local development API server.
const envBase = process.env.NEXT_PUBLIC_API_BASE?.trim();
export const API =
  envBase && envBase.length > 0
    ? envBase
    : typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : "http://localhost:8000";

// Utility function for authenticated API calls
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  
  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  // Prepend API base URL to relative URLs
  const fullUrl = url.startsWith('http') ? url : `${API}${url}`;
  
  return fetch(fullUrl, {
    ...options,
    headers,
  });
}
