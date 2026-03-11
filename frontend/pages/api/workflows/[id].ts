import type { NextApiRequest, NextApiResponse } from "next";
import { authenticatedFetch } from "@/lib/api";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { id } = req.query;
  if (typeof id !== "string") {
    res.status(400).json({ error: "Invalid workflow id" });
    return;
  }
  try {
    const r = await authenticatedFetch(`/workflows/${encodeURIComponent(id)}`);
    if (!r.ok) {
      res.status(r.status).json({ error: "Workflow not found" });
      return;
    }
    const data = await r.json();
    res.status(200).json(data);
  } catch {
    res.status(500).json({ error: "Failed to load workflow" });
  }
}
