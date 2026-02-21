import { execFile } from "child_process";
import { randomBytes } from "crypto";
import { IncomingForm } from "formidable";
import fs from "fs";
import os from "os";
import path from "path";
export const config = {
    api: {
        bodyParser: false,
    },
};
const CHECKER_UPLOAD_MAX_BYTES = 10 * 1024 * 1024;
const DOWNLOAD_TTL_MS = 10 * 60 * 1000;
const PRIVATE_DOWNLOAD_DIR = path.join(process.cwd(), ".tmp", "checker-downloads");
const ALLOWED_EXTENSIONS = new Set([".doc", ".docx"]);
const downloadTokens = new Map();
function sanitizeFilename(filename) {
    const base = path.basename(filename).replace(/[^a-zA-Z0-9._-]/g, "_");
    return base || "document.docx";
}
function cleanupExpiredDownloads() {
    const now = Date.now();
    for (const [token, record] of downloadTokens.entries()) {
        if (record.expiresAt > now) {
            continue;
        }
        downloadTokens.delete(token);
        fs.promises.unlink(record.path).catch(() => undefined);
    }
}
function buildDownloadToken(filePath, filename) {
    cleanupExpiredDownloads();
    const token = randomBytes(24).toString("hex");
    downloadTokens.set(token, {
        path: filePath,
        filename,
        expiresAt: Date.now() + DOWNLOAD_TTL_MS,
    });
    return token;
}
export default async function handler(req, res) {
    if (req.method === "GET") {
        cleanupExpiredDownloads();
        const token = typeof req.query.token === "string" ? req.query.token : "";
        if (!token) {
            res.status(400).json({ error: "Missing token" });
            return;
        }
        const record = downloadTokens.get(token);
        if (!record) {
            res.status(404).json({ error: "Download not found or expired" });
            return;
        }
        downloadTokens.delete(token);
        if (!fs.existsSync(record.path)) {
            res.status(404).json({ error: "Download not found or expired" });
            return;
        }
        res.setHeader("Content-Type", "application/octet-stream");
        res.setHeader("Content-Disposition", `attachment; filename="${record.filename}"`);
        const stream = fs.createReadStream(record.path);
        stream.on("close", () => {
            fs.promises.unlink(record.path).catch(() => undefined);
        });
        stream.pipe(res);
        return;
    }
    if (req.method !== "POST") {
        res.status(405).json({ error: "Method not allowed" });
        return;
    }
    try {
        console.log("Starting document checker API request");
        fs.mkdirSync(PRIVATE_DOWNLOAD_DIR, { recursive: true });
        const form = new IncomingForm({
            keepExtensions: true,
            uploadDir: os.tmpdir(),
            maxFiles: 1,
            maxFileSize: CHECKER_UPLOAD_MAX_BYTES,
        });
        const parsed = await new Promise((resolve, reject) => {
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
        const filePath = file.filepath || file.path;
        if (!filePath) {
            console.error("Invalid file path");
            res.status(400).json({ error: "Invalid file path" });
            return;
        }
        const originalName = sanitizeFilename(file.originalFilename || path.basename(filePath));
        const extension = path.extname(originalName).toLowerCase();
        if (!ALLOWED_EXTENSIONS.has(extension)) {
            res.status(400).json({ error: "Unsupported file type" });
            return;
        }
        console.log("Processing uploaded file");
        const results = await runChecks(filePath);
        const artifactName = `${randomBytes(16).toString("hex")}${extension}`;
        const destPath = path.join(PRIVATE_DOWNLOAD_DIR, artifactName);
        await fs.promises.copyFile(filePath, destPath);
        const token = buildDownloadToken(destPath, originalName);
        res.status(200).json({ results, downloadToken: token });
    }
    catch (error) {
        console.error("API handler error:", error);
        res.status(500).json({
            error: "Internal server error",
            details: error instanceof Error ? error.message : "Unknown error"
        });
    }
}
function runChecks(filePath) {
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
            }
            catch (e) {
                console.error("JSON parsing error:", e);
                console.error("Raw stdout:", stdout);
                reject(new Error(`Failed to parse JSON output: ${e instanceof Error ? e.message : "Unknown error"}`));
            }
        });
    });
}
