/**
 * TipTap extension: Federal Style Lint
 *
 * Real-time inline validation for federal document style rules.
 * Highlights filler words, hedging language, intensifiers, and undefined
 * acronyms using ProseMirror DecorationSet underlines.
 *
 * Rules mirror the backend `doc_validation.py` rule set.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "prosemirror-state";
import { Decoration, DecorationSet } from "prosemirror-view";

// ---------------------------------------------------------------------------
// Lint rule definitions
// ---------------------------------------------------------------------------

interface LintRule {
  pattern: RegExp;
  message: string;
  cssClass: string;
}

const STYLE_RULES: LintRule[] = [
  {
    pattern: /\b(utilize)\b/gi,
    message: "prefer 'use' over 'utilize'",
    cssClass: "federal-lint-style",
  },
  {
    pattern: /\b(in order to)\b/gi,
    message: "prefer 'to' over 'in order to'",
    cssClass: "federal-lint-style",
  },
  {
    pattern: /\b(at this point in time)\b/gi,
    message: "prefer 'now'",
    cssClass: "federal-lint-style",
  },
  {
    pattern: /\b(due to the fact that)\b/gi,
    message: "prefer 'because'",
    cssClass: "federal-lint-style",
  },
  {
    pattern: /\b(it is important to note that)\b/gi,
    message: "remove filler phrase",
    cssClass: "federal-lint-style",
  },
  {
    pattern: /\b(absolutely|definitely|certainly|really|very)\b/gi,
    message: "avoid filler intensifiers",
    cssClass: "federal-lint-style",
  },
  {
    pattern: /\b(basically|essentially|actually)\b/gi,
    message: "avoid hedging filler words",
    cssClass: "federal-lint-style",
  },
];

// ---------------------------------------------------------------------------
// Acronym detection
// ---------------------------------------------------------------------------

/** Well-known acronyms that never need expansion in federal docs. */
const COMMON_ACRONYMS = new Set([
  "US", "USA", "UK", "EU", "UN", "IT", "ID", "OK", "AM", "PM", "AI", "ML",
  "HR", "PR", "QA", "CEO", "CFO", "CTO", "COO", "VP", "MD", "PhD",
]);

/**
 * Find acronym tokens (2+ uppercase letters) that are not preceded by an
 * expansion in parentheses matching the pattern `Full Name (ACRONYM)`.
 */
function findUndefinedAcronyms(text: string): Array<{ from: number; to: number; acronym: string }> {
  const results: Array<{ from: number; to: number; acronym: string }> = [];
  const acronymPattern = /\b([A-Z]{2,})\b/g;

  // Collect all definition sites: text like "Something (ABC)" defines ABC.
  const definedAcronyms = new Set<string>();
  const defPattern = /\(([A-Z]{2,})\)/g;
  let defMatch: RegExpExecArray | null;
  while ((defMatch = defPattern.exec(text)) !== null) {
    definedAcronyms.add(defMatch[1]);
  }

  let match: RegExpExecArray | null;
  while ((match = acronymPattern.exec(text)) !== null) {
    const acronym = match[1];
    if (COMMON_ACRONYMS.has(acronym)) continue;
    if (definedAcronyms.has(acronym)) continue;

    // Skip if this occurrence is inside parentheses (it is the definition).
    const before = text.slice(Math.max(0, match.index - 1), match.index);
    const after = text.slice(match.index + acronym.length, match.index + acronym.length + 1);
    if (before === "(" && after === ")") continue;

    results.push({ from: match.index, to: match.index + acronym.length, acronym });
  }
  return results;
}

// ---------------------------------------------------------------------------
// ProseMirror decoration builder
// ---------------------------------------------------------------------------

const pluginKey = new PluginKey("federal-style-lint");

function buildDecorations(doc: any): DecorationSet {
  const decorations: Decoration[] = [];

  doc.descendants((node: any, pos: number) => {
    if (!node.isText) return;
    const text: string = node.text ?? "";
    const nodeStart = pos;

    // Style rules
    for (const rule of STYLE_RULES) {
      // Reset lastIndex for global regex
      rule.pattern.lastIndex = 0;
      let match: RegExpExecArray | null;
      while ((match = rule.pattern.exec(text)) !== null) {
        const from = nodeStart + match.index;
        const to = from + match[0].length;
        decorations.push(
          Decoration.inline(from, to, {
            class: rule.cssClass,
            title: rule.message,
          }),
        );
      }
    }

    // Acronym detection
    const acronyms = findUndefinedAcronyms(text);
    for (const acr of acronyms) {
      decorations.push(
        Decoration.inline(nodeStart + acr.from, nodeStart + acr.to, {
          class: "federal-lint-acronym",
          title: `Undefined acronym '${acr.acronym}' — provide expansion on first use`,
        }),
      );
    }
  });

  return DecorationSet.create(doc, decorations);
}

// ---------------------------------------------------------------------------
// Extension
// ---------------------------------------------------------------------------

export const federalStyleLint = Extension.create({
  name: "federal-style-lint",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: pluginKey,
        state: {
          init(_, { doc }) {
            return buildDecorations(doc);
          },
          apply(tr, oldDecorations) {
            // Only rebuild when the document actually changes.
            if (!tr.docChanged) {
              return oldDecorations.map(tr.mapping, tr.doc);
            }
            return buildDecorations(tr.doc);
          },
        },
        props: {
          decorations(state) {
            return pluginKey.getState(state) as DecorationSet;
          },
        },
      }),
    ];
  },
});
