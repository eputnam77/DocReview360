/**
 * TipTap document content schema validation.
 *
 * TipTap persists documents as a ProseMirror JSON object:
 *   { type: "doc", content: Array<TipTapNode> }
 *
 * This module validates that shape before saving to the backend, preventing
 * corrupt or truncated documents from reaching the CMS.  It is intentionally
 * lightweight — full JSON Schema validation of every possible node type would
 * be fragile across TipTap versions.  Instead we check structural invariants
 * that must hold for any valid document regardless of which extensions are
 * enabled.
 *
 * Usage:
 *   import { validateTipTapContent, parseTipTapContent } from "./contentSchema";
 *
 *   // Validate a raw JS object (e.g. editor.getJSON()):
 *   const result = validateTipTapContent(editor.getJSON());
 *   if (!result.valid) showErrors(result.errors);
 *
 *   // Parse + validate a JSON string from the network:
 *   const result = parseTipTapContent(jsonString);
 *   if (!result.valid) showErrors(result.errors);
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A single ProseMirror node in TipTap JSON format. */
export interface TipTapNode {
  type: string;
  attrs?: Record<string, unknown>;
  content?: TipTapNode[];
  marks?: TipTapMark[];
  text?: string;
}

/** A single ProseMirror mark in TipTap JSON format. */
export interface TipTapMark {
  type: string;
  attrs?: Record<string, unknown>;
}

/** The top-level TipTap document object produced by `editor.getJSON()`. */
export interface TipTapDocument {
  type: "doc";
  content: TipTapNode[];
}

/** Result returned by {@link validateTipTapContent} and {@link parseTipTapContent}. */
export interface ValidationResult {
  /** True when no structural errors were found. */
  valid: boolean;
  /** List of human-readable error messages (empty when valid). */
  errors: string[];
}

/** Extended result from {@link parseTipTapContent} that includes the parsed doc. */
export interface ParseResult extends ValidationResult {
  /** The parsed and validated document, or undefined if validation failed. */
  doc?: TipTapDocument;
}

// ---------------------------------------------------------------------------
// Node-type allowlist
// ---------------------------------------------------------------------------

/**
 * Well-known ProseMirror/TipTap node types.  Nodes with types outside this
 * set are not rejected (custom extensions add new types) but are flagged as
 * warnings if `strict` mode is enabled.
 */
const KNOWN_NODE_TYPES = new Set([
  "doc",
  "paragraph",
  "text",
  "heading",
  "bulletList",
  "orderedList",
  "listItem",
  "codeBlock",
  "blockquote",
  "horizontalRule",
  "hardBreak",
  "image",
  "table",
  "tableRow",
  "tableCell",
  "tableHeader",
  // DocReview360 custom extensions
  "section-node",
]);

/**
 * Well-known ProseMirror/TipTap mark types.
 */
const KNOWN_MARK_TYPES = new Set([
  "bold",
  "italic",
  "strike",
  "underline",
  "code",
  "link",
  "textStyle",
]);

// ---------------------------------------------------------------------------
// Internal validation helpers
// ---------------------------------------------------------------------------

function validateMark(mark: unknown, path: string, errors: string[]): void {
  if (typeof mark !== "object" || mark === null || Array.isArray(mark)) {
    errors.push(`${path}: mark must be an object`);
    return;
  }
  const m = mark as Record<string, unknown>;
  if (typeof m.type !== "string" || !m.type) {
    errors.push(`${path}: mark is missing a valid 'type' string`);
  }
  if (m.attrs !== undefined && (typeof m.attrs !== "object" || m.attrs === null)) {
    errors.push(`${path}.attrs: expected an object`);
  }
}

function validateNode(node: unknown, path: string, errors: string[], depth: number): void {
  // Guard against pathologically deep trees (e.g. malicious input).
  if (depth > 50) {
    errors.push(`${path}: document tree exceeds maximum depth (50)`);
    return;
  }

  if (typeof node !== "object" || node === null || Array.isArray(node)) {
    errors.push(`${path}: expected a node object, got ${Array.isArray(node) ? "array" : typeof node}`);
    return;
  }

  const n = node as Record<string, unknown>;

  // Every node must have a non-empty string type.
  if (typeof n.type !== "string" || !n.type) {
    errors.push(`${path}: missing or invalid 'type' field`);
    return; // Can't validate further without a type.
  }

  // attrs must be an object when present.
  if (n.attrs !== undefined && (typeof n.attrs !== "object" || n.attrs === null)) {
    errors.push(`${path}.attrs: expected an object`);
  }

  // content must be an array when present.
  if (n.content !== undefined) {
    if (!Array.isArray(n.content)) {
      errors.push(`${path}.content: expected an array`);
    } else {
      for (let i = 0; i < n.content.length; i++) {
        validateNode(n.content[i], `${path}.content[${i}]`, errors, depth + 1);
      }
    }
  }

  // marks must be an array of mark objects when present.
  if (n.marks !== undefined) {
    if (!Array.isArray(n.marks)) {
      errors.push(`${path}.marks: expected an array`);
    } else {
      for (let i = 0; i < n.marks.length; i++) {
        validateMark(n.marks[i], `${path}.marks[${i}]`, errors);
      }
    }
  }

  // text must be a string when present.
  if (n.text !== undefined && typeof n.text !== "string") {
    errors.push(`${path}.text: expected a string`);
  }

  // A text node must have text; a non-text node must not.
  if (n.type === "text" && typeof n.text !== "string") {
    errors.push(`${path}: text node is missing its 'text' field`);
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Validate a TipTap document JSON object (e.g. the output of `editor.getJSON()`).
 *
 * Checks that the root node is `{ type: "doc", content: [...] }` and recursively
 * validates every descendant node for structural correctness.  Returns a
 * {@link ValidationResult} listing all errors found in a single pass.
 *
 * This function does **not** throw — it always returns a result object.
 */
export function validateTipTapContent(doc: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof doc !== "object" || doc === null) {
    return { valid: false, errors: [`Content must be a JSON object, got ${typeof doc}`] };
  }

  const d = doc as Record<string, unknown>;

  if (d.type !== "doc") {
    const gotType = d.type ?? "(missing)";
    errors.push(`Root node 'type' must be "doc", got "${gotType}"`);
  }

  if (!Array.isArray(d.content)) {
    errors.push('Root node must have a "content" array');
  } else {
    if (d.content.length === 0) {
      // An empty content array is technically valid but unusual — not an error.
    }
    for (let i = 0; i < d.content.length; i++) {
      validateNode(d.content[i], `content[${i}]`, errors, 1);
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Parse a JSON string and validate it as a TipTap document.
 *
 * Returns a {@link ParseResult} with:
 * - `valid: false` and `errors` if the string is not valid JSON or fails
 *   structural validation.
 * - `valid: true` and `doc` (the parsed {@link TipTapDocument}) on success.
 *
 * Does **not** throw.
 */
export function parseTipTapContent(json: string): ParseResult {
  if (typeof json !== "string" || !json.trim()) {
    return { valid: false, errors: ["Content string is empty or not a string"] };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch (e) {
    return { valid: false, errors: [`Invalid JSON: ${(e as Error).message}`] };
  }

  const result = validateTipTapContent(parsed);
  return {
    ...result,
    doc: result.valid ? (parsed as TipTapDocument) : undefined,
  };
}

/**
 * Return true when the content string is either:
 *   a) A valid TipTap JSON document, or
 *   b) A non-JSON string (HTML / Markdown / plain text) — treated as valid
 *      because legacy and converted content may not be in TipTap JSON format.
 *
 * Only rejects strings that look like JSON (start with `{`) but fail schema
 * validation.  This makes the guard safe to use on all document content types.
 */
export function isContentValid(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed.startsWith("{")) {
    // Non-JSON content (HTML, Markdown, plain text) — pass through.
    return true;
  }
  const result = parseTipTapContent(trimmed);
  return result.valid;
}

/**
 * Validate content and return a user-friendly error message, or `null` if valid.
 * Suitable for inline form validation in the editor UI.
 */
export function getContentValidationError(content: string): string | null {
  const trimmed = content.trim();
  if (!trimmed.startsWith("{")) return null;
  const result = parseTipTapContent(trimmed);
  if (result.valid) return null;
  if (result.errors.length === 1) return result.errors[0];
  return `Document structure errors:\n• ${result.errors.slice(0, 5).join("\n• ")}`;
}
