// Use the configured backend URL when provided; otherwise, fall back to
// the dashboard host so requests default to the same origin as the UI.
const envBase = process.env.NEXT_PUBLIC_API_BASE?.trim();
export const API =
  envBase && envBase.length > 0
    ? envBase
    : typeof window !== "undefined"
      ? window.location.origin
      : "";
