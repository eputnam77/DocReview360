// Default to the backend FastAPI server so configuration-backed
// dropdowns (document types, phases, workflows) populate even when
// NEXT_PUBLIC_API_BASE isn't set.
export const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
