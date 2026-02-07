import type { NextApiRequest, NextApiResponse } from "next";
import { proxyToBackend } from "@/lib/apiProxy";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  const slug = req.query.slug;
  const suffix = Array.isArray(slug) ? slug.join("/") : slug;
  const path = suffix ? `/document-types/${suffix}` : "/document-types";
  return proxyToBackend(req, res, path);
}
