import type { NextApiRequest, NextApiResponse } from "next";
import { API } from "@/lib/api";

export default async function handler(
  _req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const r = await fetch(`${API}/document-types`);
    const data = r.ok ? await r.json() : [];
    res.status(200).json(data);
  } catch {
    // On network error, return an empty list so the frontend can handle gracefully
    res.status(200).json([]);
  }
}
