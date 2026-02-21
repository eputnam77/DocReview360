import type { NextApiRequest, NextApiResponse } from "next";

const apiBase = (process.env.NEXT_PUBLIC_API_BASE || process.env.DOCREVIEW360_API_BASE || "http://localhost:8000").replace(/\/$/, "");

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { role } = req.query;
  if (!role || Array.isArray(role)) {
    return res.status(400).json({ detail: "Role required" });
  }

  if (req.method !== "PUT" && req.method !== "DELETE") {
    res.setHeader("Allow", ["PUT", "DELETE"]);
    return res.status(405).json({ detail: "Method not allowed" });
  }

  try {
    const resp = await fetch(`${apiBase}/rbac/role-permissions/${encodeURIComponent(role)}`, {
      method: req.method,
      headers: {
        "Content-Type": "application/json",
        Authorization: req.headers.authorization || "",
        Cookie: req.headers.cookie || "",
      },
      body: req.method === "PUT" ? JSON.stringify(req.body || {}) : undefined,
    });

    const body = await resp.text();
    res.status(resp.status).send(body);
  } catch (error) {
    res.status(502).json({ detail: "Upstream fetch failed" });
  }
}
