import type { NextApiRequest, NextApiResponse } from "next";

const apiBase = (process.env.NEXT_PUBLIC_API_BASE || process.env.DOCREVIEW360_API_BASE || "http://localhost:8000").replace(/\/$/, "");

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "GET") {
    res.setHeader("Allow", ["GET"]);
    return res.status(405).json({ detail: "Method not allowed" });
  }

  try {
    const resp = await fetch(`${apiBase}/rbac/role-permissions`, {
      method: "GET",
      headers: {
        Authorization: req.headers.authorization || "",
        Cookie: req.headers.cookie || "",
      },
    });

    const body = await resp.text();
    res.status(resp.status).send(body);
  } catch (error) {
    res.status(502).json({ detail: "Upstream fetch failed" });
  }
}
