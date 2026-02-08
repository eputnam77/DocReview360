import { API, authenticatedFetch } from "@/lib/api";
export default async function handler(_req, res) {
    try {
        const r = await authenticatedFetch(`${API}/workflow_roles`);
        const data = r.ok ? await r.json() : [];
        res.status(200).json(data);
    }
    catch {
        res.status(200).json([]);
    }
}
