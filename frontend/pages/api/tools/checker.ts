import type { NextApiRequest, NextApiResponse } from "next";
import { IncomingForm } from "formidable";
import type * as formidable from "formidable";
import fs from "fs";
import path from "path";
import { execFile } from "child_process";

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

  const results = await runChecks(file.filepath);

  const downloadsDir = path.join(process.cwd(), "frontend/public/downloads");
  fs.mkdirSync(downloadsDir, { recursive: true });
  const destPath = path.join(downloadsDir, path.basename(file.filepath));
  await fs.promises.copyFile(file.filepath, destPath);
  const filename = path.basename(destPath);

  res.status(200).json({ results, filename });
}

function runChecks(filePath: string): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const python = process.env.VENV_PYTHON || "python3";
    const args = ["-m", "docreview360.document_checker", filePath];
    execFile(python, args, { encoding: "utf8" }, (err, stdout, stderr) => {
      if (err) {
        reject(err);
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch (e) {
        reject(e);
      }
    });
  });
}
