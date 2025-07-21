import type { NextApiRequest, NextApiResponse } from "next";
import { IncomingForm } from "formidable";
import type * as formidable from "formidable";
import fs from "fs";
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

  const results = runChecks(file.filepath);

  const downloadsDir = path.join(process.cwd(), "frontend/public/downloads");
  fs.mkdirSync(downloadsDir, { recursive: true });
  const destPath = path.join(downloadsDir, path.basename(file.filepath));
  await fs.promises.copyFile(file.filepath, destPath);
  const filename = path.basename(destPath);

  res.status(200).json({ results, filename });
}

function runChecks(filePath: string) {
  const text = fs.readFileSync(filePath, "utf8");

  const grammar: string[] = [];
  const words = text.split(/\s+/);
  for (let i = 0; i < words.length - 1; i++) {
    if (words[i] === words[i + 1]) {
      grammar.push(`repeated word '${words[i]}'`);
    }
  }

  const accessibility: string[] = [];
  const imgTag = /<img [^>]*>/gi;
  const altAttr = /alt="[^"]*"/i;
  const buttonTag = /<button([^>]*)>(.*?)<\/button>/gis;
  const ariaLabel = /aria-label="[^"]*"/i;

  let match: RegExpExecArray | null;
  while ((match = imgTag.exec(text)) !== null) {
    if (!altAttr.test(match[0])) {
      accessibility.push("image missing alt text");
    }
  }
  while ((match = buttonTag.exec(text)) !== null) {
    const attrs = match[1];
    const body = match[2];
    if (!ariaLabel.test(attrs) && body.trim() === "") {
      accessibility.push("button missing label");
    }
  }

  const styleOk = !detectAnomalies(text);

  return { grammar, accessibility, styleOk };
}

function detectAnomalies(text: string, threshold = 0.7) {
  const words = text.toLowerCase().split(/\s+/);
  let repeated = 0;
  for (let i = 0; i < words.length - 1; i++) {
    if (words[i] === words[i + 1]) repeated++;
  }
  const uniqueRatio = new Set(text).size / (text.length || 1);
  const features = [text.length / 1000, uniqueRatio, repeated];
  const weights = [0, -0.1, 1.2];
  const linear = weights.reduce((acc, w, i) => acc + w * features[i], 0);
  const score = 1 / (1 + Math.exp(-linear));
  return score >= threshold;
}
