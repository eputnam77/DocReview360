import { API } from "@/lib/api";
const METHODS_WITH_BODY = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const buildHeaders = (req, body) => {
    const headers = new Headers();
    const contentType = req.headers["content-type"];
    if (contentType) {
        headers.set("content-type", Array.isArray(contentType) ? contentType[0] : contentType);
    }
    else if (body) {
        headers.set("content-type", "application/json");
    }
    const csrfToken = req.headers["x-csrf-token"];
    if (csrfToken) {
        headers.set("x-csrf-token", Array.isArray(csrfToken) ? csrfToken[0] : csrfToken);
    }
    if (req.headers.cookie) {
        headers.set("cookie", req.headers.cookie);
    }
    return headers;
};
const serializeBody = (req) => {
    if (req.body === undefined || req.body === null) {
        return undefined;
    }
    if (typeof req.body === "string") {
        return req.body;
    }
    return JSON.stringify(req.body);
};
export const proxyToBackend = async (req, res, path) => {
    try {
        const method = req.method?.toUpperCase() ?? "GET";
        const queryString = req.url?.split("?")[1];
        const target = `${API}${path}${queryString ? `?${queryString}` : ""}`;
        const body = METHODS_WITH_BODY.has(method) ? serializeBody(req) : undefined;
        const headers = buildHeaders(req, body);
        const response = await fetch(target, {
            method,
            headers,
            body,
        });
        const responseContentType = response.headers.get("content-type");
        if (responseContentType) {
            res.setHeader("content-type", responseContentType);
        }
        res.status(response.status).send(await response.text());
    }
    catch (error) {
        console.error("Document types proxy error:", error);
        res.status(502).json({ detail: "Unable to reach document types service." });
    }
};
