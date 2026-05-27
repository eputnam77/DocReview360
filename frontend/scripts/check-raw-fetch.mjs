#!/usr/bin/env node
// SPDX-License-Identifier: MIT

import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative } from "path";
import { fileURLToPath } from "url";

const SCRIPT_DIR = fileURLToPath(new URL(".", import.meta.url));
const FRONTEND_DIR = join(SCRIPT_DIR, "..");
const PAGES_DIR = join(FRONTEND_DIR, "pages");
const SOURCE_EXTENSIONS = /\.(ts|tsx)$/;
const RAW_API_FETCH = /\bfetch\s*\(\s*(["'`])\s*\/api\//;

function collectFiles(dir) {
  const files = [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return files;
  }

  for (const entry of entries) {
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      if (entry === "node_modules" || entry === ".next" || entry.startsWith(".")) {
        continue;
      }
      files.push(...collectFiles(fullPath));
    } else if (SOURCE_EXTENSIONS.test(entry)) {
      files.push(fullPath);
    }
  }

  return files;
}

let violations = 0;

for (const file of collectFiles(PAGES_DIR)) {
  const relPath = relative(FRONTEND_DIR, file);
  const lines = readFileSync(file, "utf8").split("\n");

  lines.forEach((line, index) => {
    if (!RAW_API_FETCH.test(line)) {
      return;
    }
    console.error(`FORBIDDEN RAW FETCH: ${relPath}:${index + 1}`);
    console.error("  Rule   : use authenticatedFetch() instead of fetch('/api/...')");
    console.error(`  Line   : ${line.trim()}`);
    console.error();
    violations++;
  });
}

if (violations > 0) {
  console.error(`Found ${violations} raw fetch('/api/...') call(s). Fix them before merging.`);
  process.exit(1);
}

console.log("OK: No raw fetch('/api/...') calls found.");
