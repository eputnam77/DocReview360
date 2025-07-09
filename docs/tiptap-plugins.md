# TipTap Plugin Development

This short guide explains how DocuFlow's editor wrappers work.

Plugins export a loader function that registers toolbar actions or text
transformations. Frontend code calls the REST endpoint `/api/plugins`
to discover available wrappers and then loads each script. See the
`editor_loader.load_plugins` helper for unit tests.

## Dynamic extension toggles

Open **Editors → Tiptap** in the dashboard to try the built‑in extensions.
A small checkbox list lets you enable or disable options like `StarterKit`
and `Underline`. When you flip a switch the editor reloads with the new
extension set. Your choices are saved in the browser so the same
configuration appears next time.
