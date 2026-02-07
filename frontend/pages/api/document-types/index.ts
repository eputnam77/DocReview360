import type { NextApiRequest, NextApiResponse } from "next";
import { proxyToBackend } from "@/lib/apiProxy";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  return proxyToBackend(req, res, "/document-types");
}
