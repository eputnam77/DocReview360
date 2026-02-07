import type { NextApiRequest, NextApiResponse } from "next";
import { API, authenticatedFetch } from "@/lib/api";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { id } = req.query;
  if (typeof id !== "string") {
    res.status(400).json({ error: "Invalid workflow template id" });
    return;
  }
  const url = `${API}/workflow-templates/${encodeURIComponent(id)}`;
  try {
    if (req.method === "PUT") {
      const r = await authenticatedFetch(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body),
      });
      const data = r.ok ? await r.json() : { error: "Failed to update workflow template" };
      res.status(r.status).json(data);
      return;
    }
    if (req.method === "DELETE") {
      const r = await authenticatedFetch(url, { method: "DELETE" });
      res.status(r.status).json({});
      return;
    }
    const r = await authenticatedFetch(url);
    if (!r.ok) {
      res.status(r.status).json({ error: "Workflow template not found" });
      return;
    }
    const data = await r.json();
    res.status(200).json(data);
  } catch {
    res.status(500).json({ error: "Failed to load workflow template" });
  }
}
