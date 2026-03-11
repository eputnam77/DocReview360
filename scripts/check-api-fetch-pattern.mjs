#!/usr/bin/env node
// SPDX-License-Identifier: MIT
/**
 * check-api-fetch-pattern.mjs
 *
 * Guard against two forbidden patterns in frontend source files:
 *
 *   1. authenticatedFetch(`${API}/…`)  — relative paths must be used instead,
 *      e.g. authenticatedFetch('/endpoint'). The `authenticatedFetch` helper
 *      already prepends the API base URL, so embedding `${API}` is redundant
 *      and prevents the base URL from being overridden at runtime.
 *
 *   2. fetch(`${API}/…`)  — raw fetch calls that bypass the authenticated
 *      wrapper must not leak into shared/library code.
 *
 * Scanned directories (relative to the frontend/ folder):
 *   lib/, components/, state/, utils/, pages/
 * Scanned file extensions: .ts, .tsx, .js, .jsx
 *
 * Also scans pages/ to catch any regressions there (login.tsx exempted because
 * it intentionally uses raw fetch for the /token endpoint before a token exists).
 *
 * Exit code 0 = clean.  Exit code 1 = forbidden patterns found.
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

// Resolve paths relative to the repo root (scripts/ is one level below root)
const REPO_ROOT = join(__dirname, "..");
const FRONTEND_DIR = join(REPO_ROOT, "frontend");

/** Directories to scan, relative to FRONTEND_DIR */
const SCAN_DIRS = ["lib", "components", "state", "utils", "pages"];

/** Files explicitly exempt from this check */
const EXEMPTIONS = new Set([
  // login.tsx uses raw fetch intentionally before any token exists
  join(FRONTEND_DIR, "pages", "login.tsx"),
]);

/** Forbidden patterns: [description, regex] */
const FORBIDDEN = [
  [
    "authenticatedFetch(`${API}/…`) — use a relative path like authenticatedFetch('/endpoint') instead",
    /authenticatedFetch\s*\(\s*`\s*\$\{API\}\//,
  ],
  [
    "fetch(`${API}/…`) — use authenticatedFetch('/endpoint') instead of raw fetch with ${API}",
    /(?<![a-zA-Z])fetch\s*\(\s*`\s*\$\{API\}\//,
  ],
];

/** Recursively collect .ts / .tsx files under a directory */
function collectFiles(dir) {
  const results = [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return results; // directory may not exist in all environments
  }
  for (const entry of entries) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      // Skip node_modules and hidden directories
      if (entry === "node_modules" || entry.startsWith(".")) continue;
      results.push(...collectFiles(full));
    } else if (/\.(ts|tsx|js|jsx)$/.test(entry)) {
      results.push(full);
    }
  }
  return results;
}

let violations = 0;

for (const scanDir of SCAN_DIRS) {
  const dir = join(FRONTEND_DIR, scanDir);
  const files = collectFiles(dir);

  for (const file of files) {
    if (EXEMPTIONS.has(file)) continue;

    const relPath = relative(REPO_ROOT, file);
    const content = readFileSync(file, "utf8");
    const lines = content.split("\n");

    for (const [description, pattern] of FORBIDDEN) {
      lines.forEach((line, idx) => {
        if (pattern.test(line)) {
          console.error(`FORBIDDEN PATTERN: ${relPath}:${idx + 1}`);
          console.error(`  Rule   : ${description}`);
          console.error(`  Line   : ${line.trim()}`);
          console.error();
          violations++;
        }
      });
    }
  }
}

if (violations > 0) {
  console.error(`\nFound ${violations} forbidden fetch pattern(s). Fix them before merging.`);
  process.exit(1);
} else {
  console.log("OK: No forbidden fetch patterns found.");
  process.exit(0);
}
