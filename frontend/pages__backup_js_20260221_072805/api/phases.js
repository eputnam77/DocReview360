import { proxyToBackend } from "@/lib/apiProxy";
export default async function handler(req, res) {
    return proxyToBackend(req, res, "/phases");
}
