import { API, authenticatedFetch } from "@/lib/api";
export default async function handler(req, res) {
    try {
        const r = await authenticatedFetch(`${API}/workflows`);
        const data = r.ok ? await r.json() : [];
        res.status(200).json(data);
    }
    catch {
        // On network error, return empty list
        res.status(200).json([]);
    }
}
