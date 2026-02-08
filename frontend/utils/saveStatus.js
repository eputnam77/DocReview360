import { API, authenticatedFetch } from "../lib/api";
/**
 * Log a failed save attempt and determine the resulting status.
 * Returns "offline" when the browser reports offline mode, otherwise "error".
 */
export async function logSaveError(err) {
    try {
        await authenticatedFetch(`${API}/logs`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                level: "error",
                message: err instanceof Error ? err.message : String(err),
            }),
        });
    }
    catch {
        // ignore logging failures
    }
    return isOffline() ? "offline" : "error";
}
export function isOffline() {
    return typeof navigator !== "undefined" && navigator.onLine === false;
}
