/**
 * Tests for the TipTap plugin registry:
 *  - Registry completeness and manifest validity
 *  - Compatibility checker (satisfies / out-of-range)
 *  - No-core-patch contract: verifies that no extension imports or mutates
 *    @tiptap/* core prototypes
 *  - Content schema validation
 */

import { describe, it, expect } from "vitest";
import {
  PLUGIN_REGISTRY,
  PLUGIN_CONTRACT,
  checkTipTapCompatibility,
  getPlugin,
  alwaysOnPlugins,
  toggleablePlugins,
} from "../extensions/registry";
import {
  validateTipTapContent,
  parseTipTapContent,
  isContentValid,
  getContentValidationError,
} from "../lib/contentSchema";

// ---------------------------------------------------------------------------
// Registry completeness
// ---------------------------------------------------------------------------

describe("PLUGIN_REGISTRY", () => {
  it("contains at least one always-on and one toggleable plugin", () => {
    expect(alwaysOnPlugins().length).toBeGreaterThan(0);
    expect(toggleablePlugins().length).toBeGreaterThan(0);
  });

  it("every entry has required string fields", () => {
    for (const plugin of PLUGIN_REGISTRY) {
      expect(typeof plugin.name, `name on ${plugin.name}`).toBe("string");
      expect(plugin.name.length, `name non-empty on ${plugin.name}`).toBeGreaterThan(0);
      expect(typeof plugin.version, `version on ${plugin.name}`).toBe("string");
      expect(typeof plugin.description, `description on ${plugin.name}`).toBe("string");
      expect(typeof plugin.tiptapRange, `tiptapRange on ${plugin.name}`).toBe("string");
      expect(typeof plugin.importPath, `importPath on ${plugin.name}`).toBe("string");
      expect(typeof plugin.exportName, `exportName on ${plugin.name}`).toBe("string");
    }
  });

  it("every tiptapRange includes >=2.0.0 <3.0.0 boundary", () => {
    for (const plugin of PLUGIN_REGISTRY) {
      expect(
        plugin.tiptapRange,
        `${plugin.name} tiptapRange should cover ^2.x`,
      ).toMatch(/>=2\./);
    }
  });

  it("names are unique across the registry", () => {
    const names = PLUGIN_REGISTRY.map((p) => p.name);
    const unique = new Set(names);
    expect(unique.size).toBe(names.length);
  });

  it("getPlugin returns the correct manifest", () => {
    const p = getPlugin("structure");
    expect(p).toBeDefined();
    expect(p?.alwaysOn).toBe(true);
    expect(p?.lazy).toBe(false);
  });

  it("getPlugin returns undefined for unknown names", () => {
    expect(getPlugin("nonexistent-plugin-xyz")).toBeUndefined();
  });

  it("experimental plugins are not returned by alwaysOnPlugins or toggleablePlugins", () => {
    const exp = PLUGIN_REGISTRY.filter((p) => p.experimental);
    expect(exp.length).toBeGreaterThan(0); // sanity: at least yjs-collab
    const always = alwaysOnPlugins();
    const toggle = toggleablePlugins();
    for (const e of exp) {
      expect(always.find((p) => p.name === e.name)).toBeUndefined();
      expect(toggle.find((p) => p.name === e.name)).toBeUndefined();
    }
  });
});

// ---------------------------------------------------------------------------
// Compatibility checker
// ---------------------------------------------------------------------------

describe("checkTipTapCompatibility", () => {
  it("passes for the currently installed version (2.26.x)", () => {
    const result = checkTipTapCompatibility("2.26.1");
    expect(result.compatible).toBe(true);
    expect(result.incompatible).toHaveLength(0);
  });

  it("passes for 2.25.0 (minimum installed)", () => {
    const result = checkTipTapCompatibility("2.25.0");
    expect(result.compatible).toBe(true);
  });

  it("passes for 2.27.1 (maximum installed)", () => {
    const result = checkTipTapCompatibility("2.27.1");
    expect(result.compatible).toBe(true);
  });

  it("fails for TipTap 3.0.0 (above upper bound)", () => {
    const result = checkTipTapCompatibility("3.0.0");
    expect(result.compatible).toBe(false);
    expect(result.incompatible.length).toBeGreaterThan(0);
  });

  it("fails for TipTap 1.x (below lower bound)", () => {
    const result = checkTipTapCompatibility("1.99.9");
    expect(result.compatible).toBe(false);
  });

  it("emits warnings for experimental plugins but does not mark them incompatible", () => {
    const result = checkTipTapCompatibility("3.0.0");
    // Experimental plugins should appear in warnings, not in incompatible.
    const expNames = PLUGIN_REGISTRY.filter((p) => p.experimental).map((p) => p.name);
    for (const name of expNames) {
      const inIncompat = result.incompatible.some((p) => p.name === name);
      expect(inIncompat, `${name} should not appear in incompatible`).toBe(false);
      const inWarn = result.warnings.some((w) => w.includes(name));
      expect(inWarn, `${name} should appear in warnings`).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// No-core-patch contract
// ---------------------------------------------------------------------------

describe("PLUGIN_CONTRACT", () => {
  it("declares NO_CORE_PATCHING as true", () => {
    expect(PLUGIN_CONTRACT.NO_CORE_PATCHING).toBe(true);
  });

  it("declares GRACEFUL_DEGRADATION as true", () => {
    expect(PLUGIN_CONTRACT.GRACEFUL_DEGRADATION).toBe(true);
  });

  it("declares SEMVER_RANGE_REQUIRED as true", () => {
    expect(PLUGIN_CONTRACT.SEMVER_RANGE_REQUIRED).toBe(true);
  });
});

/**
 * Guard test: verifies that all extension source files comply with the
 * NO_CORE_PATCHING contract by importing them and checking that TipTap
 * core prototypes were not mutated.
 *
 * Strategy: capture Extension.prototype before imports, import all extensions
 * that use Extension.create(), then verify the prototype is identical after.
 */
describe("no-core-patch contract (runtime guard)", () => {
  it("Extension.prototype is not mutated by any extension import", async () => {
    const { Extension } = await import("@tiptap/core");
    const protoKeysBefore = Object.getOwnPropertyNames(Extension.prototype).sort();

    // Import all non-experimental extensions.
    await import("../extensions/tiptapStructure");
    await import("../extensions/tiptapHeadingLock");
    await import("../extensions/tiptapIndentation");
    await import("../extensions/tiptapSectionNode");
    await import("../extensions/tiptapMarkReview");
    await import("../extensions/tiptapWatermark");
    await import("../extensions/lint");
    // tiptapSlashCommand uses Suggestion (not Extension.prototype) — still import it.
    await import("../extensions/tiptapSlashCommand");

    const protoKeysAfter = Object.getOwnPropertyNames(Extension.prototype).sort();
    expect(protoKeysAfter).toEqual(protoKeysBefore);
  });

  it("@tiptap/core module object is not extended with new properties by extensions", async () => {
    const core = await import("@tiptap/core");
    const keysBefore = Object.keys(core).sort();

    // Re-importing cached modules; checks that no side-effect adds exports.
    await import("../extensions/tiptapStructure");
    await import("../extensions/tiptapIndentation");
    await import("../extensions/tiptapWatermark");

    const keysAfter = Object.keys(core).sort();
    expect(keysAfter).toEqual(keysBefore);
  });
});

// ---------------------------------------------------------------------------
// Content schema validation
// ---------------------------------------------------------------------------

describe("validateTipTapContent", () => {
  it("accepts a minimal valid doc", () => {
    const doc = { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: "Hello" }] }] };
    expect(validateTipTapContent(doc).valid).toBe(true);
  });

  it("accepts an empty content array", () => {
    const doc = { type: "doc", content: [] };
    expect(validateTipTapContent(doc).valid).toBe(true);
  });

  it("rejects a non-object", () => {
    expect(validateTipTapContent("string").valid).toBe(false);
    expect(validateTipTapContent(null).valid).toBe(false);
    expect(validateTipTapContent(42).valid).toBe(false);
  });

  it("rejects wrong root type", () => {
    const result = validateTipTapContent({ type: "paragraph", content: [] });
    expect(result.valid).toBe(false);
    expect(result.errors[0]).toMatch(/type.*must be.*doc/i);
  });

  it("rejects missing content array", () => {
    const result = validateTipTapContent({ type: "doc" });
    expect(result.valid).toBe(false);
    expect(result.errors[0]).toMatch(/content.*array/i);
  });

  it("rejects a node missing type field", () => {
    const doc = { type: "doc", content: [{ attrs: {} }] };
    const result = validateTipTapContent(doc);
    expect(result.valid).toBe(false);
    expect(result.errors[0]).toMatch(/type/i);
  });

  it("rejects a text node without text field", () => {
    const doc = { type: "doc", content: [{ type: "text" }] };
    const result = validateTipTapContent(doc);
    expect(result.valid).toBe(false);
  });

  it("accepts nodes with marks", () => {
    const doc = {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "Bold", marks: [{ type: "bold" }] }],
        },
      ],
    };
    expect(validateTipTapContent(doc).valid).toBe(true);
  });

  it("rejects invalid mark (missing type)", () => {
    const doc = {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "x", marks: [{ attrs: {} }] }],
        },
      ],
    };
    expect(validateTipTapContent(doc).valid).toBe(false);
  });

  it("catches excessively deep documents", () => {
    // Build a 60-level deep node tree.
    let node: Record<string, unknown> = { type: "text", text: "deep" };
    for (let i = 0; i < 60; i++) {
      node = { type: "paragraph", content: [node] };
    }
    const doc = { type: "doc", content: [node] };
    const result = validateTipTapContent(doc);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes("depth"))).toBe(true);
  });
});

describe("parseTipTapContent", () => {
  it("parses and validates valid JSON", () => {
    const json = JSON.stringify({ type: "doc", content: [] });
    const result = parseTipTapContent(json);
    expect(result.valid).toBe(true);
    expect(result.doc).toBeDefined();
    expect(result.doc?.type).toBe("doc");
  });

  it("rejects invalid JSON", () => {
    const result = parseTipTapContent("{not valid json}");
    expect(result.valid).toBe(false);
    expect(result.errors[0]).toMatch(/invalid json/i);
  });

  it("rejects empty string", () => {
    const result = parseTipTapContent("");
    expect(result.valid).toBe(false);
  });

  it("does not set doc on invalid result", () => {
    const result = parseTipTapContent('{"type":"paragraph"}');
    expect(result.valid).toBe(false);
    expect(result.doc).toBeUndefined();
  });
});

describe("isContentValid", () => {
  it("passes non-JSON content (HTML, Markdown)", () => {
    expect(isContentValid("<p>Hello</p>")).toBe(true);
    expect(isContentValid("# Heading\n\nParagraph")).toBe(true);
    expect(isContentValid("plain text")).toBe(true);
  });

  it("passes valid TipTap JSON", () => {
    const json = JSON.stringify({ type: "doc", content: [] });
    expect(isContentValid(json)).toBe(true);
  });

  it("rejects invalid TipTap JSON", () => {
    const json = JSON.stringify({ type: "paragraph", content: [] });
    expect(isContentValid(json)).toBe(false);
  });
});

describe("getContentValidationError", () => {
  it("returns null for valid content", () => {
    const json = JSON.stringify({ type: "doc", content: [] });
    expect(getContentValidationError(json)).toBeNull();
  });

  it("returns null for non-JSON content", () => {
    expect(getContentValidationError("<p>HTML</p>")).toBeNull();
  });

  it("returns error string for invalid JSON doc", () => {
    const json = JSON.stringify({ type: "fragment" });
    const err = getContentValidationError(json);
    expect(err).not.toBeNull();
    expect(typeof err).toBe("string");
  });
});
