import type { NextApiRequest, NextApiResponse } from "next";
import { IncomingForm } from "formidable";
import type * as formidable from "formidable";
import path from "path";

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.status(405).end();
    return;
  }

  const form = new IncomingForm({ keepExtensions: true, uploadDir: "/tmp" });
  const parsed = await new Promise<{ fields: formidable.Fields; files: formidable.Files }>((resolve, reject) => {
    form.parse(req, (err, fields, files) => {
      if (err) return reject(err);
      resolve({ fields, files });
    });
  });

  const file = parsed.files.file;
  if (!file || Array.isArray(file)) {
    res.status(400).json({ error: "File required" });
    return;
  }

  // TODO: Replace placeholder with actual DocumentCheckerToolSandbox integration
  const results = { message: "DocumentCheckerToolSandbox integration pending" };
  const filename = path.basename(file.filepath);

  res.status(200).json({ results, filename });
}
