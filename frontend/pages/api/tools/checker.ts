import { execFile } from "child_process";
import type * as formidable from "formidable";
import { IncomingForm } from "formidable";
import fs from "fs";
import type { NextApiRequest, NextApiResponse } from "next";
import path from "path";

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  try {
    console.log("Starting document checker API request");

    const form = new IncomingForm({ keepExtensions: true, uploadDir: "/tmp" });
    const parsed = await new Promise<{ fields: formidable.Fields; files: formidable.Files }>((resolve, reject) => {
      form.parse(req, (err, fields, files) => {
        if (err) {
          console.error("Form parsing error:", err);
          return reject(err);
        }
        resolve({ fields, files });
      });
    });

    const file = parsed.files.file;
    if (!file || Array.isArray(file)) {
      console.error("No file uploaded or multiple files");
      res.status(400).json({ error: "Single file required" });
      return;
    }

    // Use the correct property for file path
    const filePath = (file as any).filepath || (file as any).path;
    if (!filePath) {
      console.error("Invalid file path");
      res.status(400).json({ error: "Invalid file path" });
      return;
    }

    console.log(`Processing file: ${filePath}`);
    const results = await runChecks(filePath);
    console.log("Check results:", JSON.stringify(results, null, 2));

    // Create downloads directory
    const downloadsDir = path.join(process.cwd(), "frontend/public/downloads");
    fs.mkdirSync(downloadsDir, { recursive: true });
    const destPath = path.join(downloadsDir, path.basename(filePath));
    await fs.promises.copyFile(filePath, destPath);
    const filename = path.basename(destPath);

    console.log(`File saved to: ${destPath}`);
    res.status(200).json({ results, filename });

  } catch (error) {
    console.error("API handler error:", error);
    res.status(500).json({
      error: "Internal server error",
      details: error instanceof Error ? error.message : "Unknown error"
    });
  }
}

function runChecks(filePath: string): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const python = process.env.VENV_PYTHON || "python3";
    const args = ["-m", "docreview360.document_checker", filePath];

    console.log(`Executing: ${python} ${args.join(" ")}`);

    execFile(python, args, { encoding: "utf8" }, (err, stdout, stderr) => {
      if (err) {
        console.error("Python execution error:", err);
        console.error("stderr:", stderr);
        reject(new Error(`Python execution failed: ${err.message}`));
        return;
      }

      if (stderr) {
        console.warn("Python stderr:", stderr);
      }

      console.log("Python stdout:", stdout);

      try {
        const result = JSON.parse(stdout.trim());
        resolve(result);
      } catch (e) {
        console.error("JSON parsing error:", e);
        console.error("Raw stdout:", stdout);
        reject(new Error(`Failed to parse JSON output: ${e instanceof Error ? e.message : "Unknown error"}`));
      }
    });
  });
}
