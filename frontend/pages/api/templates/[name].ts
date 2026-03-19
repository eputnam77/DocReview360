import type { NextApiRequest, NextApiResponse } from "next";

import { buildTemplateUrlPath } from "@/lib/templatePath";

const apiBase = (
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.DOCREVIEW360_API_BASE ||
  "http://localhost:8000"
).replace(/\/$/, "");

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { name } = req.query;
  if (typeof name !== "string" || !name.trim()) {
    return res.status(400).json({ detail: "Template name required" });
  }

  if (req.method !== "GET" && req.method !== "PUT" && req.method !== "DELETE") {
    res.setHeader("Allow", ["GET", "PUT", "DELETE"]);
    return res.status(405).json({ detail: "Method not allowed" });
  }

  try {
    const resp = await fetch(`${apiBase}${buildTemplateUrlPath(name)}`, {
      method: req.method,
      headers: {
        Authorization: req.headers.authorization || "",
        Cookie: req.headers.cookie || "",
        "Content-Type": req.headers["content-type"] || "application/json",
      },
      body: req.method === "PUT" ? JSON.stringify(req.body) : undefined,
    });

    const body = await resp.text();
    res.status(resp.status).send(body);
  } catch {
    res.status(502).json({ detail: "Upstream fetch failed" });
  }
}
