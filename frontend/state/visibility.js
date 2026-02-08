import { useEffect, useState } from "react";
import { useUserStore } from "@/state/user";
import { authenticatedFetch } from "@/lib/api";
const DEFAULT_VIS = {
    stats: true,
    status: true,
    activity: true,
    logs: true,
};
export function useDashboardVisibility() {
    const username = useUserStore((s) => s.username);
    const [vis, setVis] = useState(DEFAULT_VIS);
    useEffect(() => {
        if (!username)
            return;
        authenticatedFetch("/dashboard/visibility")
            .then((r) => (r.ok ? r.json() : null))
            .then((d) => d && setVis(d))
            .catch(() => { });
    }, [username]);
    const save = () => {
        if (!username)
            return;
        authenticatedFetch("/dashboard/visibility", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(vis),
        }).catch(() => { });
    };
    return { vis, setVis, save };
}
