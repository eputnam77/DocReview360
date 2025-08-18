import type { NextApiRequest, NextApiResponse } from "next";
import { API, authenticatedFetch } from "@/lib/api";

export default async function handler(
  _req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const r = await authenticatedFetch(`${API}/workflow_roles`);
    const data = r.ok ? await r.json() : [];
    res.status(200).json(data);
  } catch {
    res.status(200).json([]);
  }
}
