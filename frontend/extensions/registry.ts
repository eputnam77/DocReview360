/**
 * DocReview360 TipTap Plugin Registry
 *
 * Single source of truth for all TipTap editor extensions used by DocReview360.
 * Every extension must have an entry here. The registry enforces:
 *
 *   1. Metadata — name, version, description for every extension.
 *   2. Compatibility — each extension declares the @tiptap/core semver range it
 *      requires; {@link checkTipTapCompatibility} surfaces breakage before runtime.
 *   3. Update safety — extensions may only use the public `Extension.create()` /
 *      `Node.create()` / `Mark.create()` APIs from @tiptap/core.  Direct
 *      prototype mutation of any @tiptap package is FORBIDDEN (see PLUGIN_CONTRACT
 *      below and docs/tiptap-plugins.md).
 *
 * Usage:
 *   import { PLUGIN_REGISTRY, checkTipTapCompatibility } from "./registry";
 *   const report = checkTipTapCompatibility("2.26.1");
 *   if (!report.compatible) console.error(report.incompatible);
 */

// ---------------------------------------------------------------------------
// Plugin contract
// ---------------------------------------------------------------------------

/**
 * Rules every extension in this registry MUST follow.
 * Violations will break forward compatibility with TipTap upgrades.
 */
export const PLUGIN_CONTRACT = {
  /**
   * Extensions MUST use the public factory APIs:
   *   Extension.create(), Node.create(), Mark.create()
   * They MUST NOT patch prototypes:
   *   @tiptap/core.prototype.xxx = ...     ← FORBIDDEN
   *   Object.assign(@tiptap/core, ...)     ← FORBIDDEN
   *   Object.defineProperty(@tiptap, ...) ← FORBIDDEN
   */
  NO_CORE_PATCHING: true,

  /**
   * Extensions MUST lazy-import optional third-party packages at runtime
   * so that the editor loads even if the optional package is absent.
   * Use:  const mod = await import("optional-pkg").catch(() => null);
   */
  GRACEFUL_DEGRADATION: true,

  /**
   * Extensions MUST declare the TipTap version range they are compatible
   * with via the `tiptapRange` field in their PluginManifest entry.
   */
  SEMVER_RANGE_REQUIRED: true,
} as const;

// ---------------------------------------------------------------------------
// Manifest type
// ---------------------------------------------------------------------------

/** Metadata for a single TipTap extension. */
export interface PluginManifest {
  /** Unique extension name — must match the `name` field in Extension.create(). */
  name: string;

  /** Semver version of this extension implementation (not @tiptap/core). */
  version: string;

  /** Human-readable description of what this extension does. */
  description: string;

  /**
   * Whether this extension is loaded lazily via dynamic import() on first use.
   * Extensions that are always-on use `lazy: false`.
   */
  lazy: boolean;

  /**
   * Whether this extension is always active in the editor (cannot be toggled
   * off by the user).
   */
  alwaysOn: boolean;

  /**
   * Semver range string describing compatible @tiptap/core versions.
   * Only `>=` and `<` constraints are supported (e.g. ">=2.0.0 <3.0.0").
   */
  tiptapRange: string;

  /**
   * Set to true for extensions that are not active in production builds.
   * Experimental extensions are excluded from compatibility checks.
   */
  experimental?: boolean;

  /**
   * Import path relative to the `frontend/extensions/` directory.
   * Used by documentation and tooling; not used at runtime.
   */
  importPath: string;

  /**
   * Named export to use from the module.
   * Use `"default"` for default exports.
   */
  exportName: string;
}

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

/**
 * All TipTap extensions registered for use in DocReview360.
 * Entries are ordered: always-on first, then lazy (alphabetical).
 */
export const PLUGIN_REGISTRY: readonly PluginManifest[] = [
  // ── Always-on extensions ─────────────────────────────────────────────────
  {
    name: "structure",
    version: "1.0.0",
    description:
      "Enforces heading-structure rules: no consecutive headings; only " +
      "paragraphs or lists may follow a heading block.",
    lazy: false,
    alwaysOn: true,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapStructure",
    exportName: "tiptapStructure",
  },
  {
    name: "slash-command",
    version: "1.0.0",
    description:
      "Slash command menu (/) for quick content insertion (headings, lists, etc.).",
    lazy: false,
    alwaysOn: true,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapSlashCommand",
    exportName: "default",
  },

  // ── Lazy / toggleable extensions ─────────────────────────────────────────
  {
    name: "heading-lock",
    version: "1.0.0",
    description:
      "Prevents keyboard deletion of H1 and H2 headings, keeping required " +
      "document sections intact.",
    lazy: true,
    alwaysOn: false,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapHeadingLock",
    exportName: "tiptapHeadingLock",
  },
  {
    name: "indentation",
    version: "1.0.0",
    description:
      "Adds indent / outdent commands via a `data-indent` attribute on " +
      "paragraphs and list items.",
    lazy: true,
    alwaysOn: false,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapIndentation",
    exportName: "tiptapIndentation",
  },
  {
    name: "lint",
    version: "1.0.0",
    description:
      'Document validation: required headings, "DRAFT" watermark detection, ' +
      "and structural rule enforcement.",
    lazy: true,
    alwaysOn: false,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./lint",
    exportName: "default",
  },
  {
    name: "federal-style-lint",
    version: "1.0.0",
    description:
      "Real-time Federal Style Validator: inline marks for style violations, " +
      "filler words, hedging, and undefined acronyms.",
    lazy: true,
    alwaysOn: false,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapFederalStyleLint",
    exportName: "federalStyleLint",
  },
  {
    name: "mark-review",
    version: "1.0.0",
    description:
      "Integration wrapper for the external MarkReview inline annotation " +
      "package. Degrades gracefully if the package is not installed.",
    lazy: true,
    alwaysOn: false,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapMarkReview",
    exportName: "tiptapMarkReview",
  },
  {
    name: "section-node",
    version: "1.0.0",
    description:
      "Draggable section blocks anchored to H2 headings, rendered as " +
      "<section> elements in the output HTML.",
    lazy: true,
    alwaysOn: false,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapSectionNode",
    exportName: "tiptapSectionNode",
  },
  {
    name: "watermark",
    version: "1.0.0",
    description:
      "DOM-overlay watermark with configurable text, rendered as a non-printing " +
      "overlay inside the editor viewport.",
    lazy: true,
    alwaysOn: false,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapWatermark",
    exportName: "tiptapWatermark",
  },

  // ── Experimental extensions (not active in v0.1) ─────────────────────────
  {
    name: "yjs-collab",
    version: "0.1.0",
    description:
      "EXPERIMENTAL: WebRTC Yjs P2P collaboration transport. " +
      "NOT active in v0.1 — production uses @hocuspocus/provider (server-backed " +
      "WebSocket) instead. Requires signalling-server config and cursor UI work " +
      "before promotion to stable.",
    lazy: true,
    alwaysOn: false,
    experimental: true,
    tiptapRange: ">=2.0.0 <3.0.0",
    importPath: "./tiptapYjsCollab",
    exportName: "tiptapYjsCollab",
  },
] as const;

// ---------------------------------------------------------------------------
// Compatibility checker
// ---------------------------------------------------------------------------

/** Result of a {@link checkTipTapCompatibility} call. */
export interface CompatibilityResult {
  /** True when every non-experimental plugin satisfies the installed version. */
  compatible: boolean;
  /** Plugins whose range does NOT include the installed version. */
  incompatible: PluginManifest[];
  /** Informational messages (experimental plugins, etc.). */
  warnings: string[];
}

/**
 * Parse a semver string "major.minor.patch" into a numeric triple.
 * Leading non-numeric characters (^, ~) are stripped.
 */
function parseSemver(v: string): [number, number, number] {
  const clean = v.replace(/^[^0-9]*/, "");
  const parts = clean.split(".").map(Number);
  return [parts[0] ?? 0, parts[1] ?? 0, parts[2] ?? 0];
}

/**
 * Return true when `version` satisfies the given `range` string.
 * Only `>=`, `>`, `<=`, `<`, and `=` constraints are supported — the minimal
 * set used in this registry.  Multiple constraints are ANDed (space-separated).
 */
function satisfies(version: string, range: string): boolean {
  const [maj, min, pat] = parseSemver(version);
  const installed = maj * 1_000_000 + min * 1_000 + pat;

  for (const constraint of range.trim().split(/\s+/)) {
    const m = constraint.match(/^(>=|>|<=|<|=)(.+)$/);
    if (!m) continue;
    const [, op, ver] = m;
    const [cm, cn, cp] = parseSemver(ver);
    const ref = cm * 1_000_000 + cn * 1_000 + cp;

    if (op === ">=" && installed < ref) return false;
    if (op === ">" && installed <= ref) return false;
    if (op === "<=" && installed > ref) return false;
    if (op === "<" && installed >= ref) return false;
    if (op === "=" && installed !== ref) return false;
  }
  return true;
}

/**
 * Check whether the installed @tiptap/core version is compatible with all
 * registered non-experimental plugins.
 *
 * Pass the resolved version string from package.json (without leading `^` or `~`).
 *
 * @example
 * import { checkTipTapCompatibility } from "./registry";
 * const report = checkTipTapCompatibility("2.26.1");
 * if (!report.compatible) {
 *   console.error("Incompatible plugins:", report.incompatible.map(p => p.name));
 * }
 */
export function checkTipTapCompatibility(installedVersion: string): CompatibilityResult {
  const incompatible: PluginManifest[] = [];
  const warnings: string[] = [];

  for (const plugin of PLUGIN_REGISTRY) {
    if (plugin.experimental) {
      warnings.push(
        `${plugin.name}@${plugin.version} is experimental and excluded from production builds.`,
      );
      continue;
    }
    if (!satisfies(installedVersion, plugin.tiptapRange)) {
      incompatible.push(plugin);
    }
  }

  return { compatible: incompatible.length === 0, incompatible, warnings };
}

// ---------------------------------------------------------------------------
// Lookup helpers
// ---------------------------------------------------------------------------

/**
 * Return the manifest for a plugin by its `name` field, or `undefined` if not
 * registered.
 */
export function getPlugin(name: string): PluginManifest | undefined {
  return PLUGIN_REGISTRY.find((p) => p.name === name);
}

/**
 * Return all non-experimental plugins that are always-on (cannot be toggled).
 */
export function alwaysOnPlugins(): PluginManifest[] {
  return PLUGIN_REGISTRY.filter((p) => p.alwaysOn && !p.experimental);
}

/**
 * Return all non-experimental plugins that are lazy-loaded and user-toggleable.
 */
export function toggleablePlugins(): PluginManifest[] {
  return PLUGIN_REGISTRY.filter((p) => p.lazy && !p.alwaysOn && !p.experimental);
}
