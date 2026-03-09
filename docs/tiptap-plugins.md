# TipTap Plugin Architecture

This document describes how DocReview360 extends TipTap without modifying the
upstream library, how to write a new extension, and how the update-safety
contract is enforced.

---

## Design Goals

1. **TipTap core stays unmodified.** DocReview360 consumes `@tiptap/core`,
   `@tiptap/starter-kit`, and individual extension packages directly from npm.
   No vendored copies. No monkey-patches. No prototype mutations.

2. **Extensions live in `frontend/extensions/`.** Each file exports one factory
   function that calls `Extension.create()` or `Node.create()`.

3. **Updates are safe.** A major TipTap upgrade should require changes only
   inside `frontend/extensions/*.ts` — never in the editor page or the registry.
   The compatibility checker surfaces breakage before runtime.

---

## Plugin Contract

Every extension MUST follow these rules (enforced by the registry and test suite):

| Rule | Description |
|------|-------------|
| **Use public APIs only** | Call `Extension.create()`, `Node.create()`, or `Mark.create()`. Never assign to `SomeClass.prototype`. |
| **No core patching** | Do not `Object.assign`, `Object.defineProperty`, or otherwise mutate any `@tiptap/*` module. |
| **Graceful degradation** | Optional third-party packages (e.g. `markreview`) must be imported with `.catch(() => null)`. The editor must load even if the package is absent. |
| **Semver range declaration** | The extension's `PluginManifest` entry must declare `tiptapRange` so the compatibility checker can catch version drift. |
| **Single responsibility** | One extension per file. Shared utilities go in `frontend/lib/`. |

These rules are validated at every CI run by the `registry.test.ts` no-core-patch tests.

---

## File Structure

```
frontend/
  extensions/
    registry.ts             ← Single source of truth for all extensions
    lint.ts                 ← Lazy: document linting rules
    tiptapHeadingLock.ts    ← Lazy: H1/H2 keyboard protection
    tiptapIndentation.ts    ← Lazy: indent/outdent commands
    tiptapMarkReview.ts     ← Lazy: MarkReview annotation wrapper
    tiptapSectionNode.ts    ← Lazy: draggable <section> blocks
    tiptapSlashCommand.tsx  ← Always-on: / command menu
    tiptapStructure.ts      ← Always-on: heading structure enforcement
    tiptapWatermark.ts      ← Lazy: DOM overlay watermark
    tiptapYjsCollab.ts      ← EXPERIMENTAL (not active in v0.1)
  lib/
    contentSchema.ts        ← TipTap JSON schema validator
  pages/editors/
    tiptap.tsx              ← Editor page — loads extensions from registry
  __tests__/
    registry.test.ts        ← Registry + no-core-patch + content schema tests
    extensions.test.ts      ← Functional tests for each extension
```

---

## The Registry

`frontend/extensions/registry.ts` exports:

| Export | Purpose |
|--------|---------|
| `PLUGIN_REGISTRY` | Immutable array of `PluginManifest` entries for all extensions |
| `PLUGIN_CONTRACT` | Named constants documenting the plugin rules |
| `checkTipTapCompatibility(version)` | Returns `{ compatible, incompatible, warnings }` |
| `getPlugin(name)` | Look up a manifest by extension name |
| `alwaysOnPlugins()` | Extensions that are always active |
| `toggleablePlugins()` | Extensions that the user can enable/disable |

### PluginManifest fields

```typescript
interface PluginManifest {
  name: string;          // matches Extension.create({ name }) value
  version: string;       // semver: this extension's implementation version
  description: string;
  lazy: boolean;         // true = dynamic import() on first toggle
  alwaysOn: boolean;     // true = cannot be disabled by user
  tiptapRange: string;   // semver range for @tiptap/core compatibility
  experimental?: boolean; // excluded from production + compat checks
  importPath: string;    // path relative to extensions/
  exportName: string;    // "default" or named export
}
```

---

## Writing a New Extension

### 1. Create the extension file

```typescript
// frontend/extensions/myExtension.ts
import { Extension } from "@tiptap/core";

export function myExtension() {
  return Extension.create({
    name: "my-extension",
    // ... addKeyboardShortcuts, addProseMirrorPlugins, etc.
  });
}
```

### 2. Register it in the registry

Add an entry to `PLUGIN_REGISTRY` in `registry.ts`:

```typescript
{
  name: "my-extension",
  version: "1.0.0",
  description: "What this extension does.",
  lazy: true,          // true for user-toggleable
  alwaysOn: false,
  tiptapRange: ">=2.0.0 <3.0.0",
  importPath: "./myExtension",
  exportName: "myExtension",
},
```

### 3. Wire it into the editor (if toggleable)

In `frontend/pages/editors/tiptap.tsx`, follow the existing lazy-load pattern:

```typescript
// State
const [myExtEnabled, setMyExtEnabled] = useState(false);
const [myExtension, setMyExtension] = useState<(() => ReturnType<typeof import("../extensions/myExtension")["myExtension"]>) | null>(null);

// In useMemo extensions array:
if (myExtEnabled && myExtension) {
  extensions.push(myExtension());
}

// Toggle handler
function handleToggleMyExt() {
  if (myExtEnabled) {
    setMyExtEnabled(false);
    setMyExtension(null);
    persistPreferences({ my_extension: false });
    return;
  }
  import("../../extensions/myExtension")
    .then((mod) => {
      setMyExtension(() => mod.myExtension);
      setMyExtEnabled(true);
      persistPreferences({ my_extension: true });
    })
    .catch(() => { /* show error state */ });
}
```

### 4. Add tests

Add functional tests to `frontend/__tests__/extensions.test.ts` and verify the
no-core-patch test still passes.

---

## Keeping TipTap Core Unmodified

### What is forbidden

```typescript
// ❌ Prototype mutation
import { Extension } from "@tiptap/core";
(Extension.prototype as any).myMethod = () => {};

// ❌ Core module patching
import * as TipTapCore from "@tiptap/core";
Object.assign(TipTapCore, { myHelper: () => {} });

// ❌ Vendoring / forking
// (Do not copy @tiptap source files into this repo)
```

### What is allowed

```typescript
// ✅ Extend via public API
import { Extension, Node, Mark } from "@tiptap/core";
export function myExt() { return Extension.create({ name: "my-ext", ... }); }

// ✅ Add ProseMirror plugins
import { Plugin } from "prosemirror-state";
addProseMirrorPlugins() { return [new Plugin({ ... })]; }

// ✅ Override built-in extension options via configure()
import StarterKit from "@tiptap/starter-kit";
StarterKit.configure({ heading: { levels: [1, 2, 3] } });
```

### Upgrade safety checklist

Before upgrading `@tiptap/*` packages:

1. Run `checkTipTapCompatibility(newVersion)` — any `incompatible` entries need
   review before the upgrade proceeds.
2. Run `npm test` — the no-core-patch tests guard against silent API changes.
3. Check TipTap's migration guide for breaking changes to `Extension.create()`
   options or removed APIs.
4. Update `tiptapRange` in each affected `PluginManifest` entry after confirming
   compatibility.

---

## Content Schema Validation

`frontend/lib/contentSchema.ts` validates TipTap JSON documents before they are
sent to the backend. Relevant exports:

| Function | Purpose |
|----------|---------|
| `validateTipTapContent(doc)` | Validate a JS object (e.g. `editor.getJSON()`) |
| `parseTipTapContent(json)` | Parse a JSON string and validate |
| `isContentValid(content)` | Pass-through for non-JSON; validate JSON strings |
| `getContentValidationError(content)` | Returns `string \| null` for inline UI use |

### Integration in the editor save path

```typescript
import { isContentValid, getContentValidationError } from "../lib/contentSchema";

async function saveDocument(content: string) {
  const error = getContentValidationError(content);
  if (error) {
    showToast({ type: "error", message: error });
    return;
  }
  await api.updateDocument(docId, content);
}
```

---

## Managing Backend (Server-Side) Plugins

Backend analysis plugins (FedStyleValidator, TextStat, LanguageTool, etc.) are
separate from TipTap editor extensions. They run on the server and are managed
via the Plugin Marketplace:

- `GET /plugin-marketplace` — list available plugins
- `POST /plugin-marketplace/install` — install from PyPI
- `PUT /plugins/{name}/enable` / `PUT /plugins/{name}/disable` — toggle

See `src/docreview360/integrations/registry.py` for the server-side plugin registry.

---

## AI Rewrite Integration

The **AI Rewrite** toolbar button calls `POST /ai/rewrite` with the selected
text.  This is not a TipTap extension — it is a toolbar action that calls the
backend and replaces the selection in the editor.  See
[`docs/ai-optimization-prompts.md`](ai-optimization-prompts.md) for the prompt
templates used by this endpoint.
