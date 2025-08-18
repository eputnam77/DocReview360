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
    });
  } catch (error) {
    console.error(`Failed to fetch ${fullUrl}:`, error);
    throw error;
  }
}
