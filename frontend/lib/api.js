// Use the configured backend URL when provided; otherwise, default to the
// local development API server.
const envBase = process.env.NEXT_PUBLIC_API_BASE?.trim();
const RUNTIME_API_BASE_KEY = "docreview360_api_base";
function _runtimeBase() {
    if (typeof window === "undefined") {
        return null;
    }
    const fromWindow = window.__DOCREVIEW360_API_BASE;
    if (typeof fromWindow === "string" && fromWindow.trim()) {
        return fromWindow.trim();
    }
    const fromStorage = window.localStorage.getItem(RUNTIME_API_BASE_KEY);
    return fromStorage && fromStorage.trim() ? fromStorage.trim() : null;
}
export const API = _runtimeBase() ?? (envBase && envBase.length > 0
    ? envBase
    : typeof window !== "undefined"
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : "http://localhost:8000");
function _resolveApiBase() {
    return _runtimeBase() ?? (envBase && envBase.length > 0
        ? envBase
        : typeof window !== "undefined"
            ? `${window.location.protocol}//${window.location.hostname}:8000`
            : "http://localhost:8000");
}
const ACCESS_TOKEN_STORAGE_KEY = "access_token";
export function getStoredAccessToken() {
    if (typeof window === "undefined") {
        return null;
    }
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}
export function setStoredAccessToken(token) {
    if (typeof window === "undefined") {
        return;
    }
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}
export function clearStoredAccessToken() {
    if (typeof window === "undefined") {
        return;
    }
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}
// Utility function for authenticated API calls
export async function authenticatedFetch(url, options = {}) {
    const headers = new Headers(options.headers);
    const storedToken = getStoredAccessToken();
    if (storedToken && !headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${storedToken}`);
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
    }
    catch (error) {
        console.error(`Failed to fetch ${fullUrl}:`, error);
        throw error;
    }
}
