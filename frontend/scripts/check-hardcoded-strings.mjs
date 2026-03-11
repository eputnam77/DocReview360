#!/usr/bin/env node
// SPDX-License-Identifier: MIT
/**
 * check-hardcoded-strings.mjs
 *
 * Scans .tsx files in frontend/pages/ and frontend/components/ for JSX text
 * content that looks like a user-facing string (3+ words) but is not wrapped
 * in a t() translation call.
 *
 * Heuristic:
 *   - JSX text nodes (content between > and <) that contain 3 or more
 *     consecutive word characters separated by spaces.
 *   - The match must NOT already sit inside a {t( ... )} expression on the
 *     same source line.
 *   - Attribute values like label="Submit Form Now" are also flagged.
 *
 * This is informational only — the script always exits with code 0.
 *
 * Usage:
 *   node scripts/check-hardcoded-strings.mjs
 *   npm run lint:i18n
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const ROOT = join(__dirname, "..");

// ---------------------------------------------------------------------------
// File discovery
// ---------------------------------------------------------------------------

/** Recursively collect .tsx files under a directory. */
function collectTsx(dir) {
  const results = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsx(full));
    } else if (entry.isFile() && entry.name.endsWith(".tsx")) {
      results.push(full);
    }
  }
  return results;
}

const scanDirs = [join(ROOT, "pages"), join(ROOT, "components")];
const files = scanDirs.flatMap((d) => {
  try {
    return collectTsx(d);
  } catch {
    return [];
  }
});

// ---------------------------------------------------------------------------
// Detection patterns
// ---------------------------------------------------------------------------

/**
 * Matches JSX text content (between > ... <) that contains 3+ words.
 * Group 1 = the text content.
 * We use a simple line-based scan rather than full AST parsing.
 */
const JSX_TEXT_RE = />([^<{}\n]{10,})</g;

/**
 * Matches attribute values like label="Three word string" or title="Some Text Here".
 * Group 1 = attribute name, Group 2 = attribute value.
 */
const ATTR_VALUE_RE = /\b(label|title|placeholder|aria-label|alt)="([^"]{6,})"/g;

/** Returns true when a line already contains a t() call. */
function lineHasTranslation(line) {
  return line.includes("t(") || line.includes("{t(");
}

/** Count the number of words in a string (sequences of \w+ separated by spaces). */
function wordCount(text) {
  return (text.trim().match(/\b\w+\b/g) ?? []).length;
}

// ---------------------------------------------------------------------------
// Scan
// ---------------------------------------------------------------------------

let totalWarnings = 0;

for (const filePath of files) {
  const rel = relative(ROOT, filePath);
  const source = readFileSync(filePath, "utf8");
  const lines = source.split("\n");

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNo = i + 1;

    if (lineHasTranslation(line)) continue;

    // Check for bare JSX text content
    let match;
    JSX_TEXT_RE.lastIndex = 0;
    while ((match = JSX_TEXT_RE.exec(line)) !== null) {
      const text = match[1].trim();
      if (wordCount(text) >= 3) {
        console.warn(`[i18n-lint] ${rel}:${lineNo} — hardcoded JSX text: "${text.slice(0, 60)}"`);
        totalWarnings++;
      }
    }

    // Check for hardcoded attribute values
    ATTR_VALUE_RE.lastIndex = 0;
    while ((match = ATTR_VALUE_RE.exec(line)) !== null) {
      const attrName = match[1];
      const value = match[2].trim();
      if (wordCount(value) >= 3) {
        console.warn(
          `[i18n-lint] ${rel}:${lineNo} — hardcoded ${attrName}="${value.slice(0, 60)}"`,
        );
        totalWarnings++;
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

if (totalWarnings === 0) {
  console.log("[i18n-lint] No hardcoded user-facing strings detected.");
} else {
  console.log(`[i18n-lint] ${totalWarnings} potential hardcoded string(s) found (informational).`);
}

// Always exit 0 — this is informational only.
process.exit(0);
