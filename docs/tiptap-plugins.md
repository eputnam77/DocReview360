# TipTap Plugins

DocReview360 uses [TipTap](https://tiptap.dev/) as its rich-text editor and ships
several custom extensions as plugins.

## Built-in Extensions

| Plugin | File | Purpose |
|---|---|---|
| Heading Lock | `tiptapHeadingLock.ts` | Prevents editing of locked heading levels |
| Federal Style Lint | `tiptapFederalStyleLint.ts` | In-editor federal style validation marks |
| Collab | (via TipTap Pro) | Real-time collaborative editing |

## Registry

All active extensions are registered in `frontend/extensions/registry.ts`.
New plugins should be added there so they are included in the editor bundle.

## Adding a Plugin

1. Create `frontend/extensions/myPlugin.ts` exporting a TipTap `Extension`.
2. Register it in `registry.ts`.
3. Add any backend hooks in `src/docreview360/tiptap/`.
4. Write tests in `tests/tiptap/`.
