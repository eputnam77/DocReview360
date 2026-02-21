import type { NextApiRequest, NextApiResponse } from "next";

const apiBase = (
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.DOCREVIEW360_API_BASE ||
  "http://localhost:8000"
).replace(/\/$/, "");

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "GET" && req.method !== "POST") {
    res.setHeader("Allow", ["GET", "POST"]);
    return res.status(405).json({ detail: "Method not allowed" });
  }

  try {
    const resp = await fetch(`${apiBase}/email-templates`, {
      method: req.method,
      headers: {
        Authorization: req.headers.authorization || "",
        Cookie: req.headers.cookie || "",
        "Content-Type": req.headers["content-type"] || "application/json",
      },
      body: req.method === "POST" ? JSON.stringify(req.body) : undefined,
    });

    const body = await resp.text();
    res.status(resp.status).send(body);
  } catch {
    res.status(502).json({ detail: "Upstream fetch failed" });
  }
}
