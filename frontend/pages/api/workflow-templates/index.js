import { API, authenticatedFetch } from "@/lib/api";
export default async function handler(req, res) {
    try {
        const url = `${API}/workflow-templates`;
        if (req.method === "POST") {
            const r = await authenticatedFetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req.body),
            });
            const data = r.ok ? await r.json() : { error: "Failed to create workflow template" };
            res.status(r.status).json(data);
            return;
        }
        const r = await authenticatedFetch(url);
        const data = r.ok ? await r.json() : [];
        res.status(200).json(data);
    }
    catch {
        res.status(200).json([]);
    }
}
