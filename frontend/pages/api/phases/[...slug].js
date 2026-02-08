import { proxyToBackend } from "@/lib/apiProxy";
export default async function handler(req, res) {
    const slug = req.query.slug;
    const suffix = Array.isArray(slug) ? slug.join("/") : slug;
    const path = suffix ? `/phases/${suffix}` : "/phases";
    return proxyToBackend(req, res, path);
}
